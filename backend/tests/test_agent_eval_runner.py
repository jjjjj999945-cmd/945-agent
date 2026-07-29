import subprocess
import sys
from pathlib import Path


def test_agent_eval_runner_reports_a_passing_deterministic_baseline():
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "backend.evals.run_agent_eval"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "945 Agent Eval" in result.stdout
    assert "Passed: 18/18" in result.stdout
    assert "Structured writes: 0" in result.stdout
