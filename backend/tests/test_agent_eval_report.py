from backend.evals.run_agent_eval import AgentEvalCase, build_eval_report


def test_eval_report_exposes_machine_readable_quality_gate():
    passing_case = AgentEvalCase("safe", "message", "ask_question", None)
    failing_case = AgentEvalCase("wrong-intent", "message", "ask_question", None)

    report = build_eval_report(
        [(passing_case, True, "intent=ask_question"), (failing_case, False, "intent=log_meal")],
        structured_writes=0,
    )

    assert report["total_cases"] == 2
    assert report["passed_cases"] == 1
    assert report["pass_rate"] == 0.5
    assert report["structured_writes"] == 0
    assert report["passed"] is False
    assert report["cases"][1]["case_id"] == "wrong-intent"
    assert report["cases"][1]["passed"] is False
