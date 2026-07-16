from fastapi import FastAPI

from backend.app.api.responses import ok
from backend.app.api.routes_advice import router as advice_router
from backend.app.api.routes_body_metrics import router as body_metrics_router
from backend.app.api.routes_daily_checkins import router as daily_checkins_router
from backend.app.api.routes_demo import router as demo_router
from backend.app.api.routes_meal_logs import router as meal_logs_router
from backend.app.api.routes_plans import router as plans_router
from backend.app.api.routes_profile import router as profile_router
from backend.app.api.routes_settings import router as settings_router
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
app.include_router(meal_logs_router)
app.include_router(body_metrics_router)
app.include_router(daily_checkins_router)
app.include_router(profile_router)
app.include_router(settings_router)
app.include_router(advice_router)


@app.get("/health")
def health() -> dict[str, object]:
    return ok({
        "status": "ok",
        "service": "945-backend"
    })
