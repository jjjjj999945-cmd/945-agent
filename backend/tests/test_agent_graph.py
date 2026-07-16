from backend.app.agents.graph import run_agent_graph
from backend.app.data.demo_data import DEMO_USER_ID


def test_agent_graph_routes_high_risk_to_safety_response():
    result = run_agent_graph(
        user_id=DEMO_USER_ID,
        locale="zh-CN",
        message="我训练时胸闷眩晕，还能继续冲重量吗？",
        context={"date": "2026-07-11"}
    )

    assert result.intent == "safety_warning"
    assert result.record_draft is None
    assert "暂停训练" in result.reply


def test_agent_graph_generates_workout_draft_without_writing():
    result = run_agent_graph(
        user_id=DEMO_USER_ID,
        locale="zh-CN",
        message="今天深蹲做了 4 组，每组 8 次，80kg。",
        context={"date": "2026-07-11"}
    )

    assert result.intent == "log_workout"
    assert result.record_draft.type == "workout_log"
    assert result.record_draft.payload["exercise_name"] == "深蹲"


def test_agent_graph_retrieves_knowledge_for_question():
    result = run_agent_graph(
        user_id=DEMO_USER_ID,
        locale="zh-CN",
        message="深蹲动作要点是什么？",
        context={"date": "2026-07-11"}
    )

    assert result.intent == "ask_question"
    assert result.record_draft is None
    assert any(chunk.metadata["topic"] == "squat" for chunk in result.rag_chunks)
    assert "结构化记录" in result.reply
