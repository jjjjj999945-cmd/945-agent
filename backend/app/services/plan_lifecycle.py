from backend.app.models.domain import CurrentPlanResponse, Plan, PlanCoverageStatus


def classify_plan_coverage(plan: Plan | None, today: str) -> PlanCoverageStatus:
    if plan is None:
        return "none"
    if plan.status == "active" and plan.start_date <= today <= plan.end_date:
        return "active_today"
    return "expired"


def current_plan_state(plan: Plan | None, today: str) -> CurrentPlanResponse:
    coverage_status = classify_plan_coverage(plan, today)
    return CurrentPlanResponse(
        plan=plan if coverage_status == "active_today" else None,
        coverage_status=coverage_status,
    )
