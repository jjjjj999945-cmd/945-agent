from collections import Counter

from backend.app.models.domain import AgentRun, AgentRunMetrics


def summarize_agent_runs(runs: list[AgentRun]) -> AgentRunMetrics:
    completed_runs = [run for run in runs if run.status == "completed"]
    failed_runs = [run for run in runs if run.status == "failed"]
    running_runs = [run for run in runs if run.status == "running"]
    interrupted_runs = [run for run in runs if run.status == "interrupted"]
    terminal_runs = completed_runs + failed_runs
    terminal_count = len(terminal_runs)
    total_runs = len(runs)
    failures_by_code = Counter(
        run.error_code for run in failed_runs if run.error_code is not None
    )

    return AgentRunMetrics(
        total_runs=total_runs,
        completed_runs=len(completed_runs),
        failed_runs=len(failed_runs),
        running_runs=len(running_runs),
        interrupted_runs=len(interrupted_runs),
        success_rate=(
            round(len(completed_runs) / terminal_count, 4) if terminal_count else 0.0
        ),
        average_duration_ms=round(
            sum(run.duration_ms for run in terminal_runs) / terminal_count,
            2,
        )
        if terminal_count
        else 0.0,
        total_input_tokens=sum(run.input_tokens for run in runs),
        total_output_tokens=sum(run.output_tokens for run in runs),
        total_logical_generations=sum(run.logical_generations for run in runs),
        total_http_attempts=sum(run.http_attempts for run in runs),
        failures_by_code=dict(failures_by_code),
    )
