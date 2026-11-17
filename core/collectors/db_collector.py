import os
import json
import time
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

from core.client.opensearch_client import opensearch_service

logger = logging.getLogger(__name__)

DB_JOBS_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "db_collectors.json"

class DBCollectorJob(BaseModel):
    id: str
    name: str
    db_type: str = "sqlite"  # sqlite, mysql, postgresql, generic_sql
    connection_url: str      # e.g., "sqlite:///./data/sample.db", "mysql+pymysql://user:pwd@127.0.0.1:3306/db"
    query: str               # e.g., "SELECT * FROM audit_logs WHERE id > :watermark ORDER BY id ASC LIMIT 500"
    watermark_column: str = "id"
    current_watermark: Any = 0
    poll_interval_sec: int = 15
    target_index: str = "db-logs"
    sourcetype: str = "database:audit"
    field_mappings: Dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_poll_time: Optional[str] = None
    last_error: Optional[str] = None
    total_rows_collected: int = 0
    total_polls: int = 0
    status: str = "idle"  # idle, running, error, stopped

class DBTestQueryRequest(BaseModel):
    db_type: str = "sqlite"
    connection_url: str
    query: str = "SELECT 1 as ping"
    limit: int = 5

class DBConnectionTestResult(BaseModel):
    success: bool
    db_type: str
    latency_ms: float
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    total_preview_rows: int = 0
    error: Optional[str] = None

class DatabaseCollectorManager:
    def __init__(self):
        self._jobs: Dict[str, DBCollectorJob] = {}
        self._worker_task: Optional[asyncio.Task] = None
        self._is_running: bool = False
        self.load_storage()

    def load_storage(self):
        DB_JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if DB_JOBS_FILE.exists():
            try:
                data = json.loads(DB_JOBS_FILE.read_text(encoding="utf-8"))
                for item in data:
                    job = DBCollectorJob(**item)
                    self._jobs[job.id] = job
                return
            except Exception as e:
                logger.error(f"Failed to load DB collectors: {e}. Reinitializing.")

        # Default sample jobs
        default_sqlite_path = Path(__file__).resolve().parent.parent.parent / "data" / "audit_sample.db"
        self._init_sample_sqlite_if_needed(default_sqlite_path)

        sample_job = DBCollectorJob(
            id="job_audit_sqlite",
            name="사내 보안 감사 로그 DB 수집기 (SQLite/MySQL)",
            db_type="sqlite",
            connection_url=f"sqlite:///{default_sqlite_path.as_posix()}",
            query="SELECT id, timestamp, actor, action, target_table, client_ip, status, detail FROM audit_log WHERE id > :watermark ORDER BY id ASC LIMIT 100",
            watermark_column="id",
            current_watermark=0,
            poll_interval_sec=15,
            target_index="db-logs",
            sourcetype="database:audit",
            field_mappings={
                "actor": "user.name",
                "client_ip": "source.ip",
                "action": "event.action",
                "detail": "message"
            },
            enabled=True
        )
        self._jobs[sample_job.id] = sample_job
        self.save_storage()

    def _init_sample_sqlite_if_needed(self, db_path: Path):
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            engine = create_engine(f"sqlite:///{db_path.as_posix()}")
            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        actor TEXT NOT NULL,
                        action TEXT NOT NULL,
                        target_table TEXT NOT NULL,
                        client_ip TEXT NOT NULL,
                        status TEXT NOT NULL,
                        detail TEXT NOT NULL
                    )
                """))
                res = conn.execute(text("SELECT COUNT(*) FROM audit_log"))
                count = res.scalar()
                if count == 0:
                    conn.execute(text("""
                        INSERT INTO audit_log (timestamp, actor, action, target_table, client_ip, status, detail)
                        VALUES
                        ('2026-11-18 06:00:01', 'admin', 'SELECT_USER', 'users', '192.168.1.100', 'SUCCESS', '전사 계정 목록 조회'),
                        ('2026-11-18 06:05:22', 'sst96', 'UPDATE_ROLE', 'roles', '10.0.0.5', 'SUCCESS', '보안관제 분석관 역할 갱신'),
                        ('2026-11-18 06:12:44', 'service_batch', 'DUMP_BACKUP', 'transactions', '172.16.0.2', 'SUCCESS', '일별 거래내역 백업 덤프 생성'),
                        ('2026-11-18 06:20:10', 'unknown_client', 'AUTH_FAIL', 'auth_tokens', '203.0.113.88', 'FAILURE', '잘못된 API Key 5회 연속 접근 시도')
                    """))
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to initialize sample sqlite db: {e}")

    def save_storage(self):
        try:
            dump_data = [j.model_dump() for j in self._jobs.values()]
            DB_JOBS_FILE.write_text(json.dumps(dump_data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to persist DB collectors storage: {e}")

    def list_jobs(self) -> List[DBCollectorJob]:
        return list(self._jobs.values())

    def get_job(self, job_id: str) -> Optional[DBCollectorJob]:
        return self._jobs.get(job_id)

    def create_job(self, job: DBCollectorJob) -> DBCollectorJob:
        if job.id in self._jobs:
            raise ValueError(f"Job with id '{job.id}' already exists.")
        self._jobs[job.id] = job
        self.save_storage()
        return job

    def update_job(self, job_id: str, updates: Dict[str, Any]) -> DBCollectorJob:
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job '{job_id}' not found.")
        
        job_data = job.model_dump()
        job_data.update(updates)
        updated_job = DBCollectorJob(**job_data)
        self._jobs[job_id] = updated_job
        self.save_storage()
        return updated_job

    def delete_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            del self._jobs[job_id]
            self.save_storage()
            return True
        return False

    def test_connection_and_query(self, req: DBTestQueryRequest) -> DBConnectionTestResult:
        start_t = time.time()
        try:
            engine = create_engine(req.connection_url, pool_pre_ping=True)
            with engine.connect() as conn:
                query_str = req.query.strip()
                # If :watermark is in query, substitute with 0 for testing
                res = conn.execute(text(query_str), {"watermark": 0, "last_val": 0})
                cols = list(res.keys()) if res.returns_rows else []
                rows = []
                if res.returns_rows:
                    fetched = res.fetchmany(req.limit)
                    for r in fetched:
                        rows.append(dict(zip(cols, [str(v) if isinstance(v, (datetime, bytes)) else v for v in r])))
                latency = round((time.time() - start_t) * 1000, 2)
                return DBConnectionTestResult(
                    success=True,
                    db_type=req.db_type,
                    latency_ms=latency,
                    columns=cols,
                    rows=rows,
                    total_preview_rows=len(rows)
                )
        except Exception as e:
            latency = round((time.time() - start_t) * 1000, 2)
            return DBConnectionTestResult(
                success=False,
                db_type=req.db_type,
                latency_ms=latency,
                error=str(e)
            )

    async def run_job_once(self, job_id: str) -> Dict[str, Any]:
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job '{job_id}' not found.")

        start_t = time.time()
        job.status = "running"
        job.total_polls += 1
        job.last_poll_time = datetime.now(timezone.utc).isoformat()

        try:
            engine = create_engine(job.connection_url)
            collected_docs = []
            max_watermark = job.current_watermark

            with engine.connect() as conn:
                params = {"watermark": job.current_watermark, "last_val": job.current_watermark}
                res = conn.execute(text(job.query), params)
                cols = list(res.keys()) if res.returns_rows else []

                if res.returns_rows:
                    rows = res.fetchall()
                    for row in rows:
                        row_dict = dict(zip(cols, row))
                        # Check watermark column
                        if job.watermark_column in row_dict:
                            w_val = row_dict[job.watermark_column]
                            if w_val is not None and (max_watermark is None or w_val > max_watermark):
                                max_watermark = w_val

                        # Synthesize ECS document
                        now_iso = datetime.now(timezone.utc).isoformat()
                        ts_val = row_dict.get("timestamp") or row_dict.get("created_at") or now_iso
                        if isinstance(ts_val, datetime):
                            ts_val = ts_val.isoformat()
                        elif not isinstance(ts_val, str):
                            ts_val = str(ts_val)

                        doc = {
                            "@timestamp": ts_val,
                            "source": f"db:{job.db_type}",
                            "sourcetype": job.sourcetype,
                            "service": f"db-collector-{job.id}",
                            "host": "database-host",
                            "level": "INFO",
                            "message": row_dict.get("detail") or row_dict.get("message") or f"Record from {job.name}",
                            "database": {
                                "job_id": job.id,
                                "job_name": job.name,
                                "type": job.db_type
                            },
                            "raw_fields": {k: (str(v) if isinstance(v, (datetime, bytes)) else v) for k, v in row_dict.items()}
                        }

                        # Apply custom field mappings
                        for src_field, target_field in job.field_mappings.items():
                            if src_field in row_dict:
                                val = row_dict[src_field]
                                doc[target_field] = val

                        collected_docs.append(doc)

            # Ingest to OpenSearch
            ingested_count = 0
            if collected_docs:
                client = opensearch_service.get_client()
                for doc in collected_docs:
                    try:
                        client.index(index=job.target_index, body=doc)
                        ingested_count += 1
                    except Exception as e:
                        logger.warning(f"Error indexing DB row to OpenSearch: {e}")

            # Update job state
            job.current_watermark = max_watermark
            job.total_rows_collected += ingested_count
            job.status = "idle"
            job.last_error = None
            self.save_storage()

            elapsed = round(time.time() - start_t, 3)
            return {
                "job_id": job.id,
                "status": "success",
                "rows_polled": len(collected_docs),
                "rows_ingested": ingested_count,
                "new_watermark": max_watermark,
                "elapsed_sec": elapsed
            }
        except Exception as e:
            job.status = "error"
            job.last_error = str(e)
            self.save_storage()
            logger.error(f"Error executing DB collector job '{job.id}': {e}")
            raise

    async def start_all(self):
        if self._is_running:
            return
        self._is_running = True
        self._worker_task = asyncio.create_task(self._scheduler_loop())
        logger.info("DB Collector background scheduler started.")

    def stop_all(self):
        self._is_running = False
        if self._worker_task:
            self._worker_task.cancel()
            self._worker_task = None
        for j in self._jobs.values():
            if j.status == "running":
                j.status = "idle"
        self.save_storage()
        logger.info("DB Collector background scheduler stopped.")

    async def _scheduler_loop(self):
        last_run_times: Dict[str, float] = {}
        while self._is_running:
            try:
                now = time.time()
                for job in list(self._jobs.values()):
                    if not job.enabled:
                        continue
                    last_t = last_run_times.get(job.id, 0)
                    if now - last_t >= max(5, job.poll_interval_sec):
                        last_run_times[job.id] = now
                        try:
                            await self.run_job_once(job.id)
                        except Exception as e:
                            logger.warning(f"DB Job {job.id} run error: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in DB collector scheduler loop: {e}")
            await asyncio.sleep(2)

db_collector_manager = DatabaseCollectorManager()
