from backend.app.agents.prompts import build_agent_instructions


def test_agent_prompt_requires_a_structured_draft_before_requesting_confirmation():
    instructions = build_agent_instructions("zh-CN")

    assert "Only request confirmation when a valid draft tool result is present." in instructions
    assert "Do not ask the user to confirm, save, or activate anything in plain text when there is no draft." in instructions
