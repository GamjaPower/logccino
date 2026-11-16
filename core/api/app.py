from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.client.opensearch_client import opensearch_service
from core.api.routes import ingest, search, analysis, admin

app = FastAPI(
    title="Logccino Core API",
    description="AI Agent MCP Log Intelligence & OpenSearch Management Platform",
    version="0.3.0"
)

# CORS 설정 (차후 프론트엔드 연동 지원)
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

@app.get("/health", tags=["Health"])
async def health_check():
    opensearch_ok = opensearch_service.ping()
    return {
        "status": "healthy" if opensearch_ok else "degraded",
        "opensearch_connected": opensearch_ok
    }

@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "Logccino Core",
        "docs": "/docs",
        "health": "/health"
    }
