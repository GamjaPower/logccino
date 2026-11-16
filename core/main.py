import uvicorn
from core.config import settings

def start():
    uvicorn.run(
        "core.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )

if __name__ == "__main__":
    start()
