from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.client.opensearch_client import opensearch_service
from core.api.routes import ingest, search, analysis, admin, install, dashboard, collector, saved_searches, users, modules, apps, auth, siem
from core.mcp.server import mcp_app

app = FastAPI(
    title="Logccino Core API & Remote MCP",
    description="Agent-Native Big Data & Real-Time Intelligence Platform for Claude",
    version="0.3.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(dashboard.router) # /dashboard, /ui
app.include_router(install.router) # /install, /install.sh, /install.py, /install.ps1
app.include_router(ingest.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(collector.router, prefix="/api/v1")
app.include_router(saved_searches.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(modules.router, prefix="/api/v1")
app.include_router(apps.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(siem.router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    from core.scheduler.engine import scheduler_engine
    scheduler_engine.start()

@app.on_event("shutdown")
async def shutdown_event():
    from core.scheduler.engine import scheduler_engine
    scheduler_engine.stop()

# Remote MCP over SSE 라우트 마운트 (Claude Desktop 원격 연동용)
if mcp_app:
    try:
        try:
            from mcp.server.transport_security import TransportSecuritySettings
            # 사내 IP(192.168.x.x) 및 k8s/AWS 도메인 접속 허용을 위해 DNS rebinding 보호 해제
            sec_settings = TransportSecuritySettings(enable_dns_rebinding_protection=False)
            sse_starlette_app = mcp_app.sse_app(transport_security=sec_settings)
        except Exception:
            sse_starlette_app = mcp_app.sse_app()

        for route in sse_starlette_app.routes:
            app.routes.append(route)
    except Exception as e:
        print(f"Warning: Failed to mount MCP SSE routes: {e}")

@app.get("/health", tags=["Health"])
async def health_check():
    opensearch_ok = opensearch_service.ping()
    return {
        "status": "healthy" if opensearch_ok else "degraded",
        "opensearch_connected": opensearch_ok,
        "mcp_sse_ready": bool(mcp_app)
    }

@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "Logccino Core & Remote MCP",
        "dashboard": "/dashboard",
        "docs": "/docs",
        "health": "/health",
        "mcp_sse_endpoint": "/sse"
    }
