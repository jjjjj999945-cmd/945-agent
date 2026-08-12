import json
from pathlib import Path

from backend.evals import run_lv4_acceptance as acceptance


ROOT = Path(__file__).resolve().parents[2]


def _check_result(
    spec: acceptance.CheckSpec,
    tmp_path: Path,
    *,
    status: str = "passed",
) -> acceptance.CheckResult:
    return acceptance.CheckResult(
        check_id=spec.check_id,
        name=spec.name,
        status=status,
        duration_ms=1.0,
        return_code=0 if status == "passed" else 1,
        failure_category=None if status == "passed" else spec.failure_category,
        log_path=tmp_path / f"{spec.check_id}.log",
    )


def _write_child_report(spec: acceptance.CheckSpec) -> None:
    if spec.artifact_path is None:
        return
    spec.artifact_path.parent.mkdir(parents=True, exist_ok=True)
    if spec.check_id == "deterministic_eval":
        report = {
            "total_cases": 50,
            "passed_cases": 50,
            "pass_rate": 1.0,
            "structured_writes": 0,
            "passed": True,
        }
    elif spec.check_id == "deepseek_eval":
        report = {
            "total_cases": 5,
            "passed_cases": 4,
            "pass_rate": 0.8,
            "structured_writes": 0,
            "average_duration_ms": 12_000,
            "total_duration_ms": 60_000,
            "total_input_tokens": 8_000,
            "total_output_tokens": 3_000,
            "total_logical_generations": 5,
            "total_http_attempts": 6,
            "failed_required_cases": [],
            "passed": True,
            "cases": [
                {
                    "case_id": "deepseek_safety_warning",
                    "passed": True,
                }
            ],
        }
    else:
        return
    spec.artifact_path.write_text(json.dumps(report), encoding="utf-8")


def test_offline_check_order_reuses_existing_quality_commands(tmp_path):
    offline, deepseek = acceptance.build_check_specs(
        ROOT,
        tmp_path,
        include_deepseek=True,
    )

    assert [item.check_id for item in offline] == [
        "backend_tests",
        "deterministic_eval",
        "frontend_build",
        "http_qa",
        "mongo_qa",
    ]
    assert deepseek is not None
    assert "--deepseek-suite" in deepseek.command
    assert "lv4" in deepseek.command


def test_offline_failure_skips_deepseek_even_when_requested(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    called_ids: list[str] = []

    def fake_executor(spec, root, log_dir):
        called_ids.append(spec.check_id)
        _write_child_report(spec)
        return _check_result(
            spec,
            tmp_path,
            status="failed" if spec.check_id == "backend_tests" else "passed",
        )

    report, exit_code = acceptance.run_acceptance(
        root=ROOT,
        json_output=tmp_path / "report.json",
        markdown_output=tmp_path / "report.md",
        include_deepseek=True,
        executor=fake_executor,
    )

    assert exit_code == 1
    assert called_ids == [
        "backend_tests",
        "deterministic_eval",
        "frontend_build",
        "http_qa",
        "mongo_qa",
    ]
    assert report["deepseek_executed"] is False
    assert report["checks"][-1]["check_id"] == "deepseek_eval"
    assert report["checks"][-1]["status"] == "skipped"


def test_missing_deepseek_key_fails_before_paid_executor(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    called_ids: list[str] = []

    def fake_executor(spec, root, log_dir):
        called_ids.append(spec.check_id)
        _write_child_report(spec)
        return _check_result(spec, tmp_path)

    report, exit_code = acceptance.run_acceptance(
        root=ROOT,
        json_output=tmp_path / "report.json",
        markdown_output=tmp_path / "report.md",
        include_deepseek=True,
        executor=fake_executor,
    )

    assert exit_code == 1
    assert "deepseek_eval" not in called_ids
    assert report["checks"][-1]["failure_category"] == "deepseek_config_error"


def test_report_contains_matrix_baseline_and_non_blocking_warnings(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    def fake_executor(spec, root, log_dir):
        _write_child_report(spec)
        return _check_result(spec, tmp_path)

    json_output = tmp_path / "report.json"
    markdown_output = tmp_path / "report.md"
    report, exit_code = acceptance.run_acceptance(
        root=ROOT,
        json_output=json_output,
        markdown_output=markdown_output,
        include_deepseek=True,
        executor=fake_executor,
    )

    markdown = markdown_output.read_text(encoding="utf-8")
    persisted = json.loads(json_output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert report["overall_status"] == "passed"
    assert report["deepseek_executed"] is True
    assert report["deepseek_baseline"]["total_cases"] == 5
    assert {item["code"] for item in report["warnings"]} == {
        "deepseek_latency_high",
        "deepseek_tokens_high",
        "deepseek_extra_http_attempts",
    }
    assert len(report["completion_matrix"]) == 8
    assert persisted["overall_status"] == report["overall_status"]
    assert "完成度矩阵" in markdown
    assert "API Key" not in markdown
    assert "test-key" not in markdown


def test_offline_report_marks_deepseek_as_not_run(tmp_path):
    def fake_executor(spec, root, log_dir):
        _write_child_report(spec)
        return _check_result(spec, tmp_path)

    report, exit_code = acceptance.run_acceptance(
        root=ROOT,
        json_output=tmp_path / "report.json",
        markdown_output=tmp_path / "report.md",
        include_deepseek=False,
        executor=fake_executor,
    )

    deepseek_capability = next(
        item for item in report["completion_matrix"] if item["capability_id"] == "deepseek_baseline"
    )
    assert exit_code == 0
    assert report["overall_status"] == "passed"
    assert report["deepseek_executed"] is False
    assert deepseek_capability["status"] == "not_run"
