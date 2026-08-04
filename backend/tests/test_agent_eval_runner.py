import subprocess
import sys
import os
from pathlib import Path


def test_agent_eval_runner_reports_a_fifty_case_deterministic_baseline():
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
    assert "Passed: 50/50" in result.stdout
    assert "Structured writes: 0" in result.stdout


def test_deepseek_eval_requires_a_key_before_running():
    root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment.pop("DEEPSEEK_API_KEY", None)
    result = subprocess.run(
        [sys.executable, "-m", "backend.evals.run_agent_eval", "--provider", "deepseek"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )

    assert result.returncode == 2
    assert "DEEPSEEK_API_KEY is required" in result.stderr
