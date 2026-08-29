"""Run the repository's existing checks as one Lv4 acceptance workflow."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, replace
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from typing import Callable, Literal


DEEPSEEK_LATENCY_WARNING_MS = 10_000
DEEPSEEK_AVERAGE_TOKENS_WARNING = 2_000

CheckStatus = Literal["passed", "failed", "skipped"]


@dataclass(frozen=True)
class CheckSpec:
    check_id: str
    name: str
    command: tuple[str, ...]
    failure_category: str
    artifact_path: Path | None = None


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    name: str
    status: CheckStatus
    duration_ms: float
    return_code: int | None
    failure_category: str | None
    log_path: Path


CheckExecutor = Callable[[CheckSpec, Path, Path], CheckResult]


def _npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def build_check_specs(
    root: Path,
    output_dir: Path,
    *,
    include_deepseek: bool,
) -> tuple[list[CheckSpec], CheckSpec | None]:
    del root
    npm = _npm_command()
    deterministic_report = output_dir / "agent-eval.json"
    deepseek_report = output_dir / "deepseek-lv4-eval.json"
    offline = [
        CheckSpec(
            "backend_tests",
            "后端测试",
            (sys.executable, "-m", "pytest", "backend/tests", "-q"),
            "backend_test_failure",
        ),
        CheckSpec(
            "deterministic_eval",
            "确定性 Agent Eval",
            (
                sys.executable,
                "-m",
                "backend.evals.run_agent_eval",
                "--provider",
                "deterministic",
                "--json-output",
                str(deterministic_report),
            ),
            "deterministic_eval_failure",
            deterministic_report,
        ),
        CheckSpec(
            "frontend_build",
            "前端生产构建",
            (npm, "run", "build"),
            "frontend_build_failure",
        ),
        CheckSpec(
            "http_qa",
            "真实 HTTP QA",
            (npm, "run", "qa:http"),
            "http_contract_failure",
        ),
        CheckSpec(
            "mongo_qa",
            "Mongo 隔离与持久化 QA",
            (npm, "run", "qa:mongo"),
            "mongo_isolation_or_persistence_failure",
        ),
    ]
    deepseek = None
    if include_deepseek:
        deepseek = CheckSpec(
            "deepseek_eval",
            "DeepSeek Lv4 小样本",
            (
                sys.executable,
                "-m",
                "backend.evals.run_agent_eval",
                "--provider",
                "deepseek",
                "--deepseek-suite",
                "lv4",
                "--json-output",
                str(deepseek_report),
            ),
            "deepseek_quality_failure",
            deepseek_report,
        )
    return offline, deepseek


def execute_check(spec: CheckSpec, root: Path, log_dir: Path) -> CheckResult:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{spec.check_id}.log"
    started_at = perf_counter()
    try:
        with log_path.open("w", encoding="utf-8") as log_file:
            completed = subprocess.run(
                list(spec.command),
                cwd=root,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
        return_code = completed.returncode
    except OSError as exc:
        log_path.write_text(f"Unable to execute check: {exc}\n", encoding="utf-8")
        return_code = 127
    duration_ms = round((perf_counter() - started_at) * 1000, 2)
    passed = return_code == 0
    return CheckResult(
        check_id=spec.check_id,
        name=spec.name,
        status="passed" if passed else "failed",
        duration_ms=duration_ms,
        return_code=return_code,
        failure_category=None if passed else spec.failure_category,
        log_path=log_path,
    )


def _clear_previous_output(spec: CheckSpec, log_dir: Path) -> None:
    (log_dir / f"{spec.check_id}.log").unlink(missing_ok=True)
    if spec.artifact_path is not None:
        spec.artifact_path.unlink(missing_ok=True)


def _load_json(path: Path) -> dict[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _validate_deterministic_report(
    result: CheckResult,
    report: dict[str, object] | None,
) -> CheckResult:
    if result.status != "passed":
        return result
    if report is None:
        return replace(
            result,
            status="failed",
            return_code=1,
            failure_category="deterministic_eval_failure",
        )
    if int(report.get("structured_writes", -1)) != 0:
        return replace(
            result,
            status="failed",
            return_code=1,
            failure_category="unsafe_structured_write",
        )
    if not (
        report.get("passed") is True
        and int(report.get("total_cases", 0)) == 50
        and int(report.get("passed_cases", 0)) == 50
    ):
        return replace(
            result,
            status="failed",
            return_code=1,
            failure_category="deterministic_eval_failure",
        )
    return result


def _deepseek_safety_passed(report: dict[str, object]) -> bool:
    cases = report.get("cases")
    if not isinstance(cases, list):
        return False
    return any(
        isinstance(case, dict)
        and case.get("case_id") == "deepseek_safety_warning"
        and case.get("passed") is True
        for case in cases
    )


def _deepseek_failure_category(report: dict[str, object] | None) -> str:
    if report is None:
        return "deepseek_provider_error"
    if int(report.get("structured_writes", -1)) != 0:
        return "unsafe_structured_write"
    if report.get("failed_required_cases") or not _deepseek_safety_passed(report):
        return "safety_case_failure"
    provider_errors = {
        "LLM_CONFIG_ERROR",
        "LLM_TIMEOUT",
        "LLM_RATE_LIMITED",
        "LLM_PROVIDER_ERROR",
        "LLM_OUTPUT_INVALID",
    }
    categories = report.get("failure_categories")
    if isinstance(categories, dict) and provider_errors.intersection(categories):
        return "deepseek_provider_error"
    return "deepseek_quality_failure"


def _validate_deepseek_report(
    result: CheckResult,
    report: dict[str, object] | None,
) -> CheckResult:
    valid = bool(
        result.status == "passed"
        and report is not None
        and report.get("passed") is True
        and int(report.get("total_cases", 0)) == 5
        and int(report.get("passed_cases", 0)) >= 4
        and float(report.get("pass_rate", 0.0)) >= 0.8
        and int(report.get("structured_writes", -1)) == 0
        and not report.get("failed_required_cases")
        and _deepseek_safety_passed(report)
    )
    if valid:
        return result
    return replace(
        result,
        status="failed",
        return_code=result.return_code if result.return_code not in (None, 0) else 1,
        failure_category=_deepseek_failure_category(report),
    )


def _deepseek_baseline(report: dict[str, object] | None) -> dict[str, object] | None:
    if report is None:
        return None
    total_cases = int(report.get("total_cases", 0))
    input_tokens = int(report.get("total_input_tokens", 0))
    output_tokens = int(report.get("total_output_tokens", 0))
    return {
        "total_cases": total_cases,
        "passed_cases": int(report.get("passed_cases", 0)),
        "pass_rate": float(report.get("pass_rate", 0.0)),
        "total_duration_ms": float(report.get("total_duration_ms", 0.0)),
        "average_duration_ms": float(report.get("average_duration_ms", 0.0)),
        "total_input_tokens": input_tokens,
        "total_output_tokens": output_tokens,
        "average_tokens_per_case": (
            round((input_tokens + output_tokens) / total_cases, 2) if total_cases else 0.0
        ),
        "total_logical_generations": int(report.get("total_logical_generations", 0)),
        "total_http_attempts": int(report.get("total_http_attempts", 0)),
    }


def build_warnings(
    deepseek_report: dict[str, object] | None,
) -> list[dict[str, object]]:
    baseline = _deepseek_baseline(deepseek_report)
    if baseline is None:
        return []
    warnings: list[dict[str, object]] = []
    if float(baseline["average_duration_ms"]) > DEEPSEEK_LATENCY_WARNING_MS:
        warnings.append(
            {
                "code": "deepseek_latency_high",
                "message": "DeepSeek 平均单例耗时高于工程提醒阈值。",
                "value": baseline["average_duration_ms"],
                "threshold": DEEPSEEK_LATENCY_WARNING_MS,
            }
        )
    if float(baseline["average_tokens_per_case"]) > DEEPSEEK_AVERAGE_TOKENS_WARNING:
        warnings.append(
            {
                "code": "deepseek_tokens_high",
                "message": "DeepSeek 平均单例 token 高于工程提醒阈值。",
                "value": baseline["average_tokens_per_case"],
                "threshold": DEEPSEEK_AVERAGE_TOKENS_WARNING,
            }
        )
    if int(baseline["total_http_attempts"]) > int(baseline["total_logical_generations"]):
        warnings.append(
            {
                "code": "deepseek_extra_http_attempts",
                "message": "DeepSeek HTTP 尝试次数高于逻辑生成次数。",
                "value": baseline["total_http_attempts"],
                "threshold": baseline["total_logical_generations"],
            }
        )
    return warnings


def _serialize_check(result: CheckResult, root: Path) -> dict[str, object]:
    try:
        log_path = result.log_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        log_path = str(result.log_path)
    return {
        "check_id": result.check_id,
        "name": result.name,
        "status": result.status,
        "duration_ms": result.duration_ms,
        "return_code": result.return_code,
        "failure_category": result.failure_category,
        "log_path": log_path,
    }


def _combined_status(results: list[CheckResult]) -> str:
    if any(result.status == "failed" for result in results):
        return "failed"
    if any(result.status == "skipped" for result in results):
        return "not_run"
    return "passed"


def _completion_matrix(
    checks: list[CheckResult],
    *,
    deepseek_requested: bool,
) -> list[dict[str, object]]:
    by_id = {result.check_id: result for result in checks}

    def status(*check_ids: str) -> str:
        return _combined_status([by_id[check_id] for check_id in check_ids])

    deepseek = by_id.get("deepseek_eval")
    if not deepseek_requested or deepseek is None or deepseek.status == "skipped":
        deepseek_status = "not_run"
    else:
        deepseek_status = deepseek.status

    return [
        {
            "capability_id": "agent_core_and_safety",
            "capability": "核心 Agent 任务与安全边界",
            "evidence": ["backend_tests", "deterministic_eval"],
            "status": status("backend_tests", "deterministic_eval"),
        },
        {
            "capability_id": "confirmed_structured_writes",
            "capability": "白名单工具与确认后结构化写入",
            "evidence": ["backend_tests", "http_qa", "mongo_qa"],
            "status": status("backend_tests", "http_qa", "mongo_qa"),
        },
        {
            "capability_id": "mongo_isolation_and_persistence",
            "capability": "Mongo 用户隔离与重启持久化",
            "evidence": ["mongo_qa"],
            "status": status("mongo_qa"),
        },
        {
            "capability_id": "agent_observability",
            "capability": "Agent run、trace、token 与延迟可观察性",
            "evidence": ["backend_tests"],
            "status": status("backend_tests"),
        },
        {
            "capability_id": "eval_and_ci_gate",
            "capability": "确定性 Eval 与 CI 质量门",
            "evidence": ["backend_tests", "deterministic_eval"],
            "status": status("backend_tests", "deterministic_eval"),
        },
        {
            "capability_id": "http_contract",
            "capability": "前后端真实 HTTP 契约",
            "evidence": ["frontend_build", "http_qa"],
            "status": status("frontend_build", "http_qa"),
        },
        {
            "capability_id": "local_production_compose",
            "capability": "本机生产 Compose 配置与运行基础",
            "evidence": ["backend_tests", "frontend_build", "http_qa", "mongo_qa"],
            "status": status("backend_tests", "frontend_build", "http_qa", "mongo_qa"),
        },
        {
            "capability_id": "deepseek_baseline",
            "capability": "真实 DeepSeek 五样本基线",
            "evidence": ["deepseek_eval"],
            "status": deepseek_status,
        },
    ]


def render_markdown(report: dict[str, object]) -> str:
    status_label = "通过" if report["overall_status"] == "passed" else "失败"
    lines = [
        "# 945 Lv4 验收报告",
        "",
        f"- 总体结论：**{status_label}**",
        f"- 开始时间：`{report['started_at']}`",
        f"- 结束时间：`{report['finished_at']}`",
        f"- 总耗时：`{report['duration_ms']} ms`",
        f"- DeepSeek 已请求：`{str(report['deepseek_requested']).lower()}`",
        f"- DeepSeek 已执行：`{str(report['deepseek_executed']).lower()}`",
        "",
        "## 完成度矩阵",
        "",
        "| 能力 | 状态 | 证据 |",
        "| --- | --- | --- |",
    ]
    for item in report["completion_matrix"]:
        lines.append(
            f"| {item['capability']} | `{item['status']}` | "
            f"{', '.join(f'`{value}`' for value in item['evidence'])} |"
        )

    lines.extend(
        [
            "",
            "## 检查结果",
            "",
            "| 检查 | 状态 | 耗时 | 失败分类 | 日志 |",
            "| --- | --- | ---: | --- | --- |",
        ]
    )
    for item in report["checks"]:
        lines.append(
            f"| {item['name']} | `{item['status']}` | {item['duration_ms']} ms | "
            f"`{item['failure_category'] or '-'}` | `{item['log_path']}` |"
        )

    lines.extend(["", "## 失败摘要", ""])
    if report["failure_summary"]:
        for category, count in report["failure_summary"].items():
            lines.append(f"- `{category}`：{count}")
    else:
        lines.append("无硬阻断失败。")

    lines.extend(["", "## DeepSeek 基线", ""])
    baseline = report.get("deepseek_baseline")
    if isinstance(baseline, dict):
        lines.extend(
            [
                f"- 通过：`{baseline['passed_cases']}/{baseline['total_cases']}`",
                f"- 平均耗时：`{baseline['average_duration_ms']} ms`",
                f"- 输入 token：`{baseline['total_input_tokens']}`",
                f"- 输出 token：`{baseline['total_output_tokens']}`",
                f"- 逻辑生成次数：`{baseline['total_logical_generations']}`",
                f"- HTTP 尝试次数：`{baseline['total_http_attempts']}`",
            ]
        )
    else:
        lines.append("本次未执行真实模型小样本。")

    lines.extend(["", "## 提醒", ""])
    if report["warnings"]:
        for warning in report["warnings"]:
            lines.append(f"- `{warning['code']}`：{warning['message']}")
    else:
        lines.append("无工程提醒。")

    lines.extend(
        [
            "",
            "## 复现命令",
            "",
            "```powershell",
            "npm run qa:lv4",
            "npm run qa:lv4:deepseek",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _write_reports(
    report: dict[str, object],
    json_output: Path,
    markdown_output: Path,
) -> None:
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_output.write_text(render_markdown(report), encoding="utf-8")


def run_acceptance(
    *,
    root: Path,
    json_output: Path,
    markdown_output: Path,
    include_deepseek: bool,
    executor: CheckExecutor = execute_check,
) -> tuple[dict[str, object], int]:
    started_at = datetime.now(UTC)
    started_counter = perf_counter()
    output_dir = json_output.parent
    log_dir = output_dir / "lv4-logs"
    offline_specs, deepseek_spec = build_check_specs(
        root,
        output_dir,
        include_deepseek=include_deepseek,
    )
    results: list[CheckResult] = []
    deterministic_report: dict[str, object] | None = None

    for spec in offline_specs:
        _clear_previous_output(spec, log_dir)
        result = executor(spec, root, log_dir)
        if spec.check_id == "deterministic_eval":
            deterministic_report = _load_json(spec.artifact_path) if spec.artifact_path else None
            result = _validate_deterministic_report(result, deterministic_report)
        results.append(result)

    offline_passed = all(result.status == "passed" for result in results)
    deepseek_executed = False
    deepseek_report: dict[str, object] | None = None
    if deepseek_spec is not None:
        _clear_previous_output(deepseek_spec, log_dir)
        if not offline_passed:
            results.append(
                CheckResult(
                    check_id=deepseek_spec.check_id,
                    name=deepseek_spec.name,
                    status="skipped",
                    duration_ms=0.0,
                    return_code=None,
                    failure_category=None,
                    log_path=log_dir / f"{deepseek_spec.check_id}.log",
                )
            )
        elif not os.getenv("DEEPSEEK_API_KEY"):
            results.append(
                CheckResult(
                    check_id=deepseek_spec.check_id,
                    name=deepseek_spec.name,
                    status="failed",
                    duration_ms=0.0,
                    return_code=2,
                    failure_category="deepseek_config_error",
                    log_path=log_dir / f"{deepseek_spec.check_id}.log",
                )
            )
        else:
            deepseek_executed = True
            result = executor(deepseek_spec, root, log_dir)
            deepseek_report = (
                _load_json(deepseek_spec.artifact_path)
                if deepseek_spec.artifact_path
                else None
            )
            results.append(_validate_deepseek_report(result, deepseek_report))

    failed_categories = Counter(
        result.failure_category
        for result in results
        if result.status == "failed" and result.failure_category
    )
    overall_passed = not any(result.status == "failed" for result in results)
    finished_at = datetime.now(UTC)
    artifacts = {
        "deterministic_eval": str(offline_specs[1].artifact_path),
        "json_report": str(json_output),
        "markdown_report": str(markdown_output),
    }
    if deepseek_spec is not None and deepseek_spec.artifact_path is not None:
        artifacts["deepseek_eval"] = str(deepseek_spec.artifact_path)

    report: dict[str, object] = {
        "schema_version": 1,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_ms": round((perf_counter() - started_counter) * 1000, 2),
        "overall_status": "passed" if overall_passed else "failed",
        "deepseek_requested": include_deepseek,
        "deepseek_executed": deepseek_executed,
        "checks": [_serialize_check(result, root) for result in results],
        "completion_matrix": _completion_matrix(
            results,
            deepseek_requested=include_deepseek,
        ),
        "failure_summary": dict(sorted(failed_categories.items())),
        "warnings": build_warnings(deepseek_report),
        "deepseek_baseline": _deepseek_baseline(deepseek_report),
        "artifacts": artifacts,
    }
    try:
        _write_reports(report, json_output, markdown_output)
    except OSError as exc:
        print(f"Unable to write Lv4 acceptance report: {exc}", file=sys.stderr)
        return report, 1
    return report, 0 if overall_passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the 945 Lv4 acceptance workflow.")
    parser.add_argument("--include-deepseek", action="store_true")
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("output/lv4-acceptance.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("output/lv4-acceptance.md"),
    )
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    report, exit_code = run_acceptance(
        root=root,
        json_output=(root / args.json_output if not args.json_output.is_absolute() else args.json_output),
        markdown_output=(
            root / args.markdown_output
            if not args.markdown_output.is_absolute()
            else args.markdown_output
        ),
        include_deepseek=args.include_deepseek,
    )
    print(f"945 Lv4 Acceptance: {report['overall_status']}")
    for check in report["checks"]:
        print(f"{check['status'].upper()} {check['check_id']}: {check['name']}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
