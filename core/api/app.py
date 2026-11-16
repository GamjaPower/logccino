from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.client.opensearch_client import opensearch_service
from core.api.routes import ingest, search, analysis, admin
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
app.include_router(ingest.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")

# Remote MCP over SSE 라우트 마운트 (Claude Desktop 원격 연동용)
if mcp_app:
    try:
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
        "docs": "/docs",
        "health": "/health",
        "mcp_sse_endpoint": "/sse"
    }
