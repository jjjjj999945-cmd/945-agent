from fastapi import FastAPI

from backend.app.api.responses import ok
from backend.app.api.routes_demo import router as demo_router
from backend.app.api.routes_plans import router as plans_router
from backend.app.api.routes_workout_logs import router as workout_logs_router


app = FastAPI(
    title="945 Backend",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.include_router(demo_router)
app.include_router(plans_router)
app.include_router(workout_logs_router)


@app.get("/health")
def health() -> dict[str, object]:
    return ok({
        "status": "ok",
        "service": "945-backend"
    })
