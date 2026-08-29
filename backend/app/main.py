from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.responses import ok
from backend.app.api.routes_advice import router as advice_router
from backend.app.api.routes_auth import router as auth_router
from backend.app.api.routes_agent import router as agent_router
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5177",
        "http://localhost:5177",
        "http://127.0.0.1:8080",
        "http://localhost:8080"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(demo_router)
app.include_router(auth_router)
app.include_router(plans_router)
app.include_router(workout_logs_router)
app.include_router(meal_logs_router)
app.include_router(body_metrics_router)
app.include_router(daily_checkins_router)
app.include_router(profile_router)
app.include_router(settings_router)
app.include_router(advice_router)
app.include_router(agent_router)


@app.get("/health")
def health() -> dict[str, object]:
    return ok({
        "status": "ok",
        "service": "945-backend"
    })
