from fastapi import FastAPI

from backend.app.api.responses import ok


app = FastAPI(
    title="945 Backend",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.get("/health")
def health() -> dict[str, object]:
    return ok({
        "status": "ok",
        "service": "945-backend"
    })
