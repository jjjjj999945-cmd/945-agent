from fastapi import FastAPI

from backend.app.api.responses import ok
from backend.app.api.routes_demo import router as demo_router


app = FastAPI(
    title="945 Backend",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.include_router(demo_router)


@app.get("/health")
def health() -> dict[str, object]:
    return ok({
        "status": "ok",
        "service": "945-backend"
    })
