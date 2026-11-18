import os
import signal
import socket
import subprocess
import time
import httpx
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from core.client.opensearch_client import opensearch_service
from core.config import settings
from core.collectors.snmp_telegraf import snmp_collector, TelegrafSNMPConfig
from core.collectors.db_collector import db_collector_manager, DBCollectorJob, DBTestQueryRequest, DBConnectionTestResult
from core.collectors.syslog_ports import (
    syslog_ports_manager,
    SyslogPortConfig,
    SyslogPortCreateRequest,
    SyslogPortUpdateRequest
)
from core.apps.connector_store import connector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collector", tags=["Collector"])
collectors_router = APIRouter(prefix="/collectors", tags=["Collectors Manager"])

COLLECTOR_DIR = Path(__file__).resolve().parent.parent.parent.parent / "collectors" / "syslog-collector"
BINARY_PATH = COLLECTOR_DIR / "target" / "release" / "logccino-syslog-collector"
PID_FILE = Path("/tmp/logccino-syslog-collector.pid")

class CollectorStartRequest(BaseModel):
    port: int = 1514
    metrics_port: int = 1515
    backend_url: str = "http://127.0.0.1:8000/api/v1/ingest/syslog"

class CollectorTestEventRequest(BaseModel):
    event_type: str = "ssh_failed"  # ssh_failed, ssh_accepted, sudo_escalation, ufw_block, pam_failure
    protocol: str = "udp"            # udp or tcp
    port: int = 1514                 # target port (1514 default or any configured port)
    custom_message: Optional[str] = None

class CollectorManager:
    _process: Optional[subprocess.Popen] = None

    @classmethod
    def get_binary_path(cls) -> Path:
        return BINARY_PATH

    @classmethod
    def is_binary_available(cls) -> bool:
        return BINARY_PATH.is_file() and os.access(BINARY_PATH, os.X_OK)

    @classmethod
    def get_pid_from_file(cls) -> Optional[int]:
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text().strip())
                os.kill(pid, 0)
                return pid
            except (ValueError, OSError):
                if PID_FILE.exists():
                    try:
                        PID_FILE.unlink()
                    except OSError:
                        pass
        return None

    @classmethod
    async def get_live_metrics(cls, metrics_port: int = 1515) -> Optional[Dict[str, Any]]:
        url = f"http://127.0.0.1:{metrics_port}/"
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    return res.json()
        except Exception:
            pass
        return None

    @classmethod
    async def get_status(cls) -> Dict[str, Any]:
        binary_exists = cls.is_binary_available()
        pid = cls.get_pid_from_file()
        live_metrics = await cls.get_live_metrics()

        is_running = (pid is not None) or (live_metrics is not None)

        ports_list = syslog_ports_manager.list_ports()
        return {
            "status": "running" if is_running else "stopped",
            "pid": pid,
            "binary_path": str(BINARY_PATH),
            "binary_exists": binary_exists,
            "port": 1514,
            "protocols": ["UDP", "TCP"],
            "udp_listening": is_running,
            "tcp_listening": is_running,
            "configured_ports": ports_list,
            "total_ports_count": len(ports_list),
            "metrics": live_metrics or {
                "uptime_seconds": 0,
                "received_total": 0,
                "parsed_total": 0,
                "forwarded_total": 0,
                "security_alerts_total": 0,
                "throughput_eps": 0.0
            }
        }

    @classmethod
    def start(cls, port: int = 1514, metrics_port: int = 1515, backend_url: str = "http://127.0.0.1:8000/api/v1/ingest/syslog") -> Dict[str, Any]:
        if not cls.is_binary_available():
            raise HTTPException(
                status_code=400,
                detail=f"Syslog collector binary not found at {BINARY_PATH}. Please compile with 'cargo build --release'."
            )

        current_pid = cls.get_pid_from_file()
        if current_pid:
            return {"status": "already_running", "pid": current_pid, "port": port}

        cmd = [
            str(BINARY_PATH),
            "--port", str(port),
            "--metrics-port", str(metrics_port),
            "--backend-url", backend_url
        ]

        log_file = open("/tmp/logccino-syslog-collector.log", "a")
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid
        )
        cls._process = proc
        PID_FILE.write_text(str(proc.pid))

        time.sleep(0.3)
        if proc.poll() is not None:
            PID_FILE.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail="Syslog collector terminated immediately upon startup. Check /tmp/logccino-syslog-collector.log")

        return {"status": "started", "pid": proc.pid, "port": port, "metrics_port": metrics_port, "protocols": ["UDP", "TCP"]}

    @classmethod
    def stop(cls) -> Dict[str, Any]:
        pid = cls.get_pid_from_file()
        if not pid:
            return {"status": "not_running"}

        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        except OSError:
            pass
        finally:
            PID_FILE.unlink(missing_ok=True)
            cls._process = None

        return {"status": "stopped", "terminated_pid": pid}

    @classmethod
    def send_test_packet_udp(cls, message: str, port: int = 1514) -> bool:
        """UDP 패킷으로 Syslog 메시지 전송"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(message.encode("utf-8"), ("127.0.0.1", port))
            return True
        finally:
            sock.close()

    @classmethod
    def send_test_packet_tcp(cls, message: str, port: int = 1514) -> bool:
        """TCP 소켓으로 Syslog 메시지 전송"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        try:
            sock.connect(("127.0.0.1", port))
            msg_bytes = message.encode("utf-8")
            if not msg_bytes.endswith(b"\n"):
                msg_bytes += b"\n"
            sock.sendall(msg_bytes)
            return True
        except Exception as e:
            logger.error(f"TCP syslog send error: {e}")
            return False
        finally:
            sock.close()

    @classmethod
    def send_test_packet(cls, message: str, port: int = 1514, protocol: str = "udp") -> bool:
        if protocol.lower() == "tcp":
            return cls.send_test_packet_tcp(message, port)
        return cls.send_test_packet_udp(message, port)


# =====================================================================
# 1. Existing /collector/... Endpoints (100% Backward Compatible)
# =====================================================================

@router.get("/status")
async def get_collector_status():
    """보안 Syslog 수집기 상태 및 실시간 처리 통계 조회"""
    return await CollectorManager.get_status()

@router.post("/start")
async def start_collector(req: CollectorStartRequest = CollectorStartRequest()):
    """보안 Syslog 수집기 데몬 시작"""
    return CollectorManager.start(
        port=req.port,
        metrics_port=req.metrics_port,
        backend_url=req.backend_url
    )

@router.post("/stop")
async def stop_collector():
    """보안 Syslog 수집기 데몬 중지"""
    return CollectorManager.stop()

@router.post("/restart")
async def restart_collector(req: CollectorStartRequest = CollectorStartRequest()):
    """보안 Syslog 수집기 데몬 재시작"""
    CollectorManager.stop()
    time.sleep(0.5)
    return CollectorManager.start(
        port=req.port,
        metrics_port=req.metrics_port,
        backend_url=req.backend_url
    )

@router.post("/test-event")
async def send_test_event(req: CollectorTestEventRequest):
    """
    보안 위협 테스트 로그를 Syslog 포트(UDP or TCP 1514)로 인젝션하여 실시간 탐지 테스트
    """
    ts = time.strftime("%b %d %H:%M:%S")

    presets = {
        "ssh_failed": f"<{3*8 + 3}>{ts} bastion-gateway sshd[38291]: Failed password for invalid user hacker from 203.0.113.88 port 59281 ssh2",
        "ssh_accepted": f"<{3*8 + 6}>{ts} bastion-gateway sshd[38300]: Accepted publickey for sst96 from 192.168.1.50 port 52140 ssh2: RSA SHA256:abc123xyz",
        "sudo_escalation": f"<{10*8 + 5}>{ts} prod-db01 sudo:   devops : TTY=pts/2 ; PWD=/opt/data ; USER=root ; COMMAND=/bin/bash -i",
        "ufw_block": f"<{0*8 + 4}>{ts} edge-firewall kernel: [UFW BLOCK] IN=eth0 OUT= MAC=00:11:22:33:44:55 SRC=198.51.100.120 DST=192.168.1.1 LEN=40 TOS=0x00 PREC=0x00 TTL=240 ID=54321 PROTO=TCP SPT=49152 DPT=22 WINDOW=1024 RES=0x00 SYN URGP=0",
        "pam_failure": f"<{10*8 + 3}>{ts} sso-server pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost=203.0.113.99  user=root"
    }

    raw_msg = req.custom_message or presets.get(req.event_type, presets["ssh_failed"])
    proto = req.protocol.lower() if req.protocol else "udp"
    target_port = req.port if req.port else 1514
    success = CollectorManager.send_test_packet(raw_msg, port=target_port, protocol=proto)

    return {
        "status": "injected" if success else "failed",
        "protocol": proto.upper(),
        "port": target_port,
        "event_type": req.event_type,
        "raw_message": raw_msg,
        "target": f"127.0.0.1:{target_port} ({proto.upper()})",
        "target_udp": f"127.0.0.1:{target_port}"
    }

@router.get("/security-events")
async def get_recent_security_events(limit: int = 50):
    client = opensearch_service.get_client()
    index_pattern = f"main,{settings.opensearch_index_prefix}-*"

    query = {
        "size": limit,
        "sort": [{"@timestamp": {"order": "desc"}}],
        "query": {
            "bool": {
                "should": [
                    {"term": {"sourcetype": "syslog"}},
                    {"term": {"service": "security-syslog"}},
                    {"exists": {"field": "security.action"}},
                    {"exists": {"field": "attributes.security.action"}}
                ],
                "minimum_should_match": 1
            }
        }
    }

    try:
        res = client.search(index=index_pattern, body=query)
        hits = [hit["_source"] for hit in res.get("hits", {}).get("hits", [])]
        total = res.get("hits", {}).get("total", {}).get("value", len(hits))
        return {
            "total": total,
            "count": len(hits),
            "events": hits
        }
    except Exception as e:
        return {
            "total": 0,
            "count": 0,
            "events": [],
            "error": str(e)
        }


# =====================================================================
# 2. Dedicated /collectors/... Endpoints for Unified Ingestion Manager
# =====================================================================

@collectors_router.get("/overview")
async def get_all_collectors_overview():
    """모든 수집기(Syslog TCP/UDP, Telegraf SNMP, Python DB Ingestion, Connectors)의 종합 상태 조회"""
    syslog_status = await CollectorManager.get_status()
    snmp_status = snmp_collector.get_status()
    db_jobs = db_collector_manager.list_jobs()
    connectors = connector_store.list_available_connectors()

    total_active = 0
    if syslog_status["status"] == "running":
        total_active += 1
    if snmp_status["status"] == "running":
        total_active += 1
    active_db_jobs = sum(1 for j in db_jobs if j.enabled)
    if active_db_jobs > 0:
        total_active += 1

    return {
        "status": "healthy",
        "total_active_engines": total_active,
        "syslog": syslog_status,
        "snmp_telegraf": snmp_status,
        "database": {
            "total_jobs": len(db_jobs),
            "active_jobs": active_db_jobs,
            "total_records_ingested": sum(j.total_rows_collected for j in db_jobs),
            "jobs_summary": [{"id": j.id, "name": j.name, "db_type": j.db_type, "status": j.status, "watermark": j.current_watermark} for j in db_jobs]
        },
        "connectors": {
            "total_available": len(connectors),
            "installed_count": len(connector_store.list_installed_connectors())
        }
    }

# --- Syslog Sub-endpoints ---
@collectors_router.get("/syslog/status")
async def collectors_syslog_status():
    return await CollectorManager.get_status()

@collectors_router.post("/syslog/start")
async def collectors_syslog_start(req: CollectorStartRequest = CollectorStartRequest()):
    return CollectorManager.start(port=req.port, metrics_port=req.metrics_port, backend_url=req.backend_url)

@collectors_router.post("/syslog/stop")
async def collectors_syslog_stop():
    return CollectorManager.stop()

@collectors_router.post("/syslog/restart")
async def collectors_syslog_restart(req: CollectorStartRequest = CollectorStartRequest()):
    CollectorManager.stop()
    time.sleep(0.5)
    return CollectorManager.start(port=req.port, metrics_port=req.metrics_port, backend_url=req.backend_url)

@collectors_router.post("/syslog/test-packet")
async def collectors_syslog_test_packet(req: CollectorTestEventRequest):
    return await send_test_event(req)

# --- Syslog Multi-Port & Parser Binding Endpoints ---
@collectors_router.get("/syslog/ports")
async def collectors_list_syslog_ports():
    """모든 등록된 Syslog 포트와 연결된 파싱 규칙 상세 조회"""
    return syslog_ports_manager.list_ports()

@collectors_router.post("/syslog/ports")
async def collectors_add_syslog_port(req: SyslogPortCreateRequest):
    """새로운 Syslog 수집 포트 추가 및 파싱 규칙 연결"""
    try:
        return await syslog_ports_manager.add_port(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@collectors_router.put("/syslog/ports/{port}")
async def collectors_update_syslog_port(port: int, req: SyslogPortUpdateRequest):
    """Syslog 포트 설정(파싱 규칙, 프로토콜, 대상 인덱스 등) 수정"""
    updated = await syslog_ports_manager.update_port(port, req)
    if not updated:
        raise HTTPException(status_code=404, detail=f"포트 {port}를 찾을 수 없습니다.")
    return updated

@collectors_router.delete("/syslog/ports/{port}")
async def collectors_delete_syslog_port(port: int):
    """Syslog 포트 삭제 (기본 1514 포트는 삭제 불가)"""
    try:
        success = await syslog_ports_manager.delete_port(port)
        if not success:
            raise HTTPException(status_code=404, detail=f"포트 {port}를 찾을 수 없습니다.")
        return {"status": "deleted", "port": port}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@collectors_router.post("/syslog/ports/{port}/toggle")
async def collectors_toggle_syslog_port(port: int, enabled: Optional[bool] = Query(None)):
    """Syslog 포트 활성화/비활성화 토글"""
    updated = await syslog_ports_manager.toggle_port(port, enabled)
    if not updated:
        raise HTTPException(status_code=404, detail=f"포트 {port}를 찾을 수 없습니다.")
    return updated

# --- SNMP Telegraf Sub-endpoints ---
@collectors_router.get("/snmp/status")
async def collectors_snmp_status():
    return snmp_collector.get_status()

@collectors_router.get("/snmp/config")
async def collectors_snmp_config():
    return {
        "config": snmp_collector.get_config(),
        "toml_preview": snmp_collector.generate_toml_config()
    }

@collectors_router.post("/snmp/config")
async def collectors_snmp_save_config(config: TelegrafSNMPConfig):
    path = snmp_collector.save_config(config)
    return {"status": "saved", "path": str(path), "config": config}

@collectors_router.post("/snmp/start")
async def collectors_snmp_start():
    return await snmp_collector.start()

@collectors_router.post("/snmp/stop")
async def collectors_snmp_stop():
    return snmp_collector.stop()

@collectors_router.post("/snmp/test-poll")
async def collectors_snmp_test_poll(agent_url: str = Query("udp://192.168.1.1:161"), community: str = Query("public")):
    return await snmp_collector.test_poll(agent_url, community)

@collectors_router.post("/snmp/ingest")
async def collectors_snmp_ingest_metrics(payload: List[Dict[str, Any]] = Body(...)):
    """Telegraf HTTP Output에서 전달되는 메트릭 적재 엔드포인트"""
    count = snmp_collector.ingest_metrics_batch(payload)
    return {"status": "success", "ingested_count": count}

# --- Database Ingestion Collector Sub-endpoints ---
@collectors_router.get("/db/jobs", response_model=List[DBCollectorJob])
async def collectors_db_list_jobs():
    return db_collector_manager.list_jobs()

@collectors_router.post("/db/jobs", response_model=DBCollectorJob)
async def collectors_db_create_job(job: DBCollectorJob):
    return db_collector_manager.create_job(job)

@collectors_router.put("/db/jobs/{job_id}", response_model=DBCollectorJob)
async def collectors_db_update_job(job_id: str, updates: Dict[str, Any]):
    return db_collector_manager.update_job(job_id, updates)

@collectors_router.delete("/db/jobs/{job_id}")
async def collectors_db_delete_job(job_id: str):
    success = db_collector_manager.delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "deleted", "job_id": job_id}

@collectors_router.post("/db/jobs/{job_id}/run-now")
async def collectors_db_run_now(job_id: str):
    return await db_collector_manager.run_job_once(job_id)

@collectors_router.post("/db/test-connection", response_model=DBConnectionTestResult)
async def collectors_db_test_connection(req: DBTestQueryRequest):
    return db_collector_manager.test_connection_and_query(req)

@collectors_router.post("/db/start")
async def collectors_db_start():
    await db_collector_manager.start_all()
    return {"status": "started"}

@collectors_router.post("/db/stop")
async def collectors_db_stop():
    db_collector_manager.stop_all()
    return {"status": "stopped"}
