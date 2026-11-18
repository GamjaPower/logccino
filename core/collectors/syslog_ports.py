"""
Logccino Multi-Port Syslog Manager
- 기본 포트: 1514 (UDP & TCP)
- 추가 포트 동적 생성 및 관리 (포트별 프로토콜 설정)
- 포트별 독립적 필드 파싱 규칙(Parser Profile) 연결
- 수신 시 포트에 연결된 파싱 규칙으로 실시간 필드 정규화 및 인덱싱
"""

import os
import json
import socket
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from core.collectors.parsing_rules import parsing_rule_manager, ParsingRule
from core.ingestion.pipeline import IngestionPipeline

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
SYSLOG_PORTS_FILE = DATA_DIR / "syslog_ports.json"

DEFAULT_PORT = 1514


class SyslogPortConfig(BaseModel):
    port: int
    name: str
    description: Optional[str] = None
    protocol: str = "BOTH"  # BOTH, UDP, TCP
    parser_rule_id: str = "rule-default-syslog"
    target_index: str = "main"
    enabled: bool = True
    status: str = "active"  # active, stopped, error
    error_message: Optional[str] = None
    received_total: int = 0
    parsed_total: int = 0
    forwarded_total: int = 0
    error_total: int = 0
    last_event_time: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: Optional[str] = None


class SyslogPortCreateRequest(BaseModel):
    port: int
    name: str
    description: Optional[str] = None
    protocol: str = "BOTH"
    parser_rule_id: str = "rule-default-syslog"
    target_index: str = "main"
    enabled: bool = True


class SyslogPortUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    protocol: Optional[str] = None
    parser_rule_id: Optional[str] = None
    target_index: Optional[str] = None
    enabled: Optional[bool] = None


# UDP Protocol Handler for Asyncio
class SyslogUdpProtocol(asyncio.DatagramProtocol):
    def __init__(self, port: int, manager: "SyslogMultiPortManager"):
        self.port = port
        self.manager = manager
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr):
        try:
            text = data.decode("utf-8", errors="replace")
            client_ip = addr[0] if addr else None
            asyncio.create_task(self.manager.process_received_message(self.port, text, client_ip))
        except Exception as e:
            logger.error(f"[UDP Port {self.port}] Receive error: {e}")


class SyslogMultiPortManager:
    def __init__(self):
        self._ports: Dict[int, SyslogPortConfig] = {}
        self._udp_transports: Dict[int, asyncio.DatagramTransport] = {}
        self._tcp_servers: Dict[int, asyncio.Server] = {}
        self._pipeline = IngestionPipeline()
        self._load_storage()

    def _load_storage(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if SYSLOG_PORTS_FILE.exists():
            try:
                data = json.loads(SYSLOG_PORTS_FILE.read_text(encoding="utf-8"))
                for item in data:
                    cfg = SyslogPortConfig(**item)
                    self._ports[cfg.port] = cfg
            except Exception as e:
                logger.warning(f"Failed to load {SYSLOG_PORTS_FILE}: {e}")

        # Ensure default port 1514 exists
        if DEFAULT_PORT not in self._ports:
            default_cfg = SyslogPortConfig(
                port=DEFAULT_PORT,
                name="기본 보안 Syslog 리스너 (기본포트)",
                description="기본 1514 포트 (UDP/TCP) - Linux, SSH, Sudo, UFW 표준 보안 로그 수집 및 탐지",
                protocol="BOTH",
                parser_rule_id="rule-default-syslog",
                target_index="main",
                enabled=True,
                status="active"
            )
            self._ports[DEFAULT_PORT] = default_cfg
            self._save_storage()

    def _save_storage(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            data = [p.model_dump() for p in self._ports.values()]
            SYSLOG_PORTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save syslog ports: {e}")

    def list_ports(self) -> List[Dict[str, Any]]:
        """모든 포트 설정 목록과 연결된 파싱 규칙 상세 정보 함께 반환"""
        results = []
        for port_cfg in sorted(self._ports.values(), key=lambda p: (0 if p.port == DEFAULT_PORT else 1, p.port)):
            rule = parsing_rule_manager.get_rule(port_cfg.parser_rule_id)
            item = port_cfg.model_dump()
            item["is_default_port"] = (port_cfg.port == DEFAULT_PORT)
            item["parser_rule"] = {
                "id": rule.id if rule else port_cfg.parser_rule_id,
                "name": rule.name if rule else "알 수 없는 파싱 규칙",
                "parser_type": rule.parser_type if rule else "syslog_standard",
                "description": rule.description if rule else ""
            }
            results.append(item)
        return results

    def get_port(self, port: int) -> Optional[SyslogPortConfig]:
        return self._ports.get(port)

    async def add_port(self, req: SyslogPortCreateRequest) -> SyslogPortConfig:
        if req.port in self._ports:
            raise ValueError(f"포트 {req.port}는 이미 등록되어 있습니다.")

        if req.port < 1 or req.port > 65535:
            raise ValueError("포트 번호는 1 ~ 65535 사이여야 합니다.")

        # Verify parser rule exists
        rule = parsing_rule_manager.get_rule(req.parser_rule_id)
        if not rule:
            req.parser_rule_id = "rule-default-syslog"

        cfg = SyslogPortConfig(
            port=req.port,
            name=req.name,
            description=req.description,
            protocol=req.protocol.upper(),
            parser_rule_id=req.parser_rule_id,
            target_index=req.target_index or "main",
            enabled=req.enabled,
            status="active" if req.enabled else "stopped"
        )
        self._ports[cfg.port] = cfg
        self._save_storage()

        if cfg.enabled:
            await self.start_port_listener(cfg.port)

        return cfg

    async def update_port(self, port: int, req: SyslogPortUpdateRequest) -> Optional[SyslogPortConfig]:
        cfg = self._ports.get(port)
        if not cfg:
            return None

        data = cfg.model_dump()
        for k, v in req.model_dump(exclude_unset=True).items():
            if v is not None:
                data[k] = v

        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        updated_cfg = SyslogPortConfig(**data)
        self._ports[port] = updated_cfg
        self._save_storage()

        # Restart listener with new config
        await self.stop_port_listener(port)
        if updated_cfg.enabled:
            await self.start_port_listener(port)

        return updated_cfg

    async def delete_port(self, port: int) -> bool:
        if port == DEFAULT_PORT:
            raise ValueError(f"기본 포트 {DEFAULT_PORT}는 삭제할 수 없습니다.")

        if port not in self._ports:
            return False

        await self.stop_port_listener(port)
        del self._ports[port]
        self._save_storage()
        return True

    async def toggle_port(self, port: int, enabled: Optional[bool] = None) -> Optional[SyslogPortConfig]:
        cfg = self._ports.get(port)
        if not cfg:
            return None

        new_val = not cfg.enabled if enabled is None else enabled
        cfg.enabled = new_val
        cfg.status = "active" if new_val else "stopped"
        cfg.updated_at = datetime.now(timezone.utc).isoformat()
        self._save_storage()

        if new_val:
            await self.start_port_listener(port)
        else:
            await self.stop_port_listener(port)

        return cfg

    # -------------------------------------------------------------
    # Runtime Socket Listeners (UDP & TCP Asyncio)
    # -------------------------------------------------------------
    async def start_port_listener(self, port: int):
        cfg = self._ports.get(port)
        if not cfg or not cfg.enabled:
            return

        loop = asyncio.get_running_loop()
        proto = cfg.protocol.upper()

        # 1. UDP Listener
        if proto in ("BOTH", "UDP"):
            if port not in self._udp_transports:
                try:
                    transport, _ = await loop.create_datagram_endpoint(
                        lambda: SyslogUdpProtocol(port, self),
                        local_addr=("0.0.0.0", port)
                    )
                    self._udp_transports[port] = transport
                    cfg.status = "active"
                    cfg.error_message = None
                    logger.info(f"Syslog UDP listener started on 0.0.0.0:{port} (Parser: {cfg.parser_rule_id})")
                except OSError as e:
                    logger.warning(f"Could not bind UDP on port {port}: {e}")
                    if port == DEFAULT_PORT:
                        cfg.status = "active (Rust Daemon)"
                    else:
                        cfg.status = "error"
                        cfg.error_message = str(e)

        # 2. TCP Listener
        if proto in ("BOTH", "TCP"):
            if port not in self._tcp_servers:
                try:
                    server = await asyncio.start_server(
                        lambda r, w: self._handle_tcp_connection(port, r, w),
                        "0.0.0.0", port
                    )
                    self._tcp_servers[port] = server
                    cfg.status = "active"
                    cfg.error_message = None
                    logger.info(f"Syslog TCP listener started on 0.0.0.0:{port} (Parser: {cfg.parser_rule_id})")
                except OSError as e:
                    logger.warning(f"Could not bind TCP on port {port}: {e}")
                    if port == DEFAULT_PORT:
                        cfg.status = "active (Rust Daemon)"
                    else:
                        cfg.status = "error"
                        cfg.error_message = str(e)

        self._save_storage()

    async def _handle_tcp_connection(self, port: int, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        client_addr = None
        try:
            peer = writer.get_extra_info("peername")
            if peer:
                client_addr = peer[0]
            while not reader.at_eof():
                line = await reader.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace")
                if text.strip():
                    await self.process_received_message(port, text, client_addr)
        except Exception as e:
            logger.error(f"[TCP Port {port}] Error reading from client: {e}")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def stop_port_listener(self, port: int):
        # Stop UDP
        if port in self._udp_transports:
            try:
                self._udp_transports[port].close()
            except Exception:
                pass
            del self._udp_transports[port]

        # Stop TCP
        if port in self._tcp_servers:
            try:
                self._tcp_servers[port].close()
                await self._tcp_servers[port].wait_closed()
            except Exception:
                pass
            del self._tcp_servers[port]

        cfg = self._ports.get(port)
        if cfg:
            cfg.status = "stopped"
            self._save_storage()
        logger.info(f"Syslog listeners stopped on port {port}")

    async def start_all_listeners(self):
        for port, cfg in list(self._ports.items()):
            if cfg.enabled:
                await self.start_port_listener(port)

    async def stop_all_listeners(self):
        for port in list(self._ports.keys()):
            await self.stop_port_listener(port)

    # -------------------------------------------------------------
    # Ingestion & Parsing Execution
    # -------------------------------------------------------------
    async def process_received_message(self, port: int, raw_text: str, client_ip: Optional[str] = None):
        cfg = self._ports.get(port)
        if not cfg:
            cfg = self._ports.get(DEFAULT_PORT)
            if not cfg:
                return

        cfg.received_total += 1
        cfg.last_event_time = datetime.now(timezone.utc).isoformat()

        # 1. Retrieve the linked parsing rule
        rule = parsing_rule_manager.get_rule(cfg.parser_rule_id)
        if not rule:
            rule = parsing_rule_manager.get_rule("rule-default-syslog")

        try:
            # 2. Execute parsing according to rule
            record = parsing_rule_manager.execute_parser(rule, raw_text, client_addr=client_ip)
            cfg.parsed_total += 1

            # Tag port metadata
            record["port"] = port
            record["attributes"]["collector_port"] = port
            record["attributes"]["parser_rule_id"] = rule.id
            record["attributes"]["parser_rule_name"] = rule.name
            record["index"] = cfg.target_index or "main"

            # 3. Ingest into OpenSearch pipeline
            target_idx = cfg.target_index or "main"
            self._pipeline.ingest_records([record], target_index=target_idx)
            cfg.forwarded_total += 1

        except Exception as e:
            cfg.error_total += 1
            logger.error(f"[Port {port} - Rule {cfg.parser_rule_id}] Parsing/Ingest error: {e}")

        # Periodically persist stats (or save every 20 events)
        if cfg.received_total % 20 == 0:
            self._save_storage()


# Singleton Instance
syslog_ports_manager = SyslogMultiPortManager()
