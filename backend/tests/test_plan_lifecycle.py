from fastapi.testclient import TestClient

from backend.app.models import domain
from backend.app.data.demo_data import DEMO_PLAN
from backend.app.main import app
from backend.app.services import demo_store
from backend.app.services.plan_lifecycle import classify_plan_coverage


client = TestClient(app)


def make_plan(*, status: str, start_date: str, end_date: str):
    return DEMO_PLAN.model_copy(
        update={
            "status": status,
            "start_date": start_date,
            "end_date": end_date,
        }
    )


def test_classify_plan_coverage_returns_active_today_for_active_plan_covering_today():
    plan = make_plan(status="active", start_date="2026-07-26", end_date="2026-08-01")

    assert classify_plan_coverage(plan, "2026-07-26") == "active_today"


def test_classify_plan_coverage_returns_expired_for_active_plan_ending_before_today():
    plan = make_plan(status="active", start_date="2026-07-11", end_date="2026-07-17")

    assert classify_plan_coverage(plan, "2026-07-26") == "expired"


def test_classify_plan_coverage_returns_expired_for_draft_plan_covering_today():
    plan = make_plan(status="draft", start_date="2026-07-26", end_date="2026-08-01")

    assert classify_plan_coverage(plan, "2026-07-26") == "expired"


def test_classify_plan_coverage_returns_expired_for_archived_plan_covering_today():
    plan = make_plan(status="archived", start_date="2026-07-26", end_date="2026-08-01")

    assert classify_plan_coverage(plan, "2026-07-26") == "expired"


def test_plan_lifecycle_state_aliases_the_current_plan_response_contract():
    assert getattr(domain, "PlanLifecycleState", None) is domain.CurrentPlanResponse


def test_current_plan_endpoint_returns_none_state_instead_of_404_when_user_has_no_plan(monkeypatch):
    monkeypatch.setattr(demo_store, "plans", [])

    response = client.get("/api/plans/current?user_id=demo-user-945")

    assert response.status_code == 200
    assert response.json()["data"] == {"plan": None, "coverage_status": "none"}
