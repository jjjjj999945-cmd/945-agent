from backend.app.rag.retriever import retrieve_knowledge


def test_retriever_returns_exercise_knowledge_with_metadata():
    results = retrieve_knowledge("深蹲动作要点", locale="zh-CN")

    assert results
    assert results[0].metadata["source_type"] == "exercise_knowledge"
    assert results[0].metadata["topic"] == "squat"
    assert "髋" in results[0].content or "膝" in results[0].content


def test_retriever_returns_nutrition_knowledge():
    results = retrieve_knowledge("蛋白质和外食估算", locale="zh-CN")

    assert any(result.metadata["source_type"] == "nutrition_knowledge" for result in results)


def test_retriever_returns_product_rules_for_confirmation():
    results = retrieve_knowledge("训练记录需要确认吗", locale="zh-CN")

    assert any(result.metadata["source_type"] == "product_rule" for result in results)
    assert any("确认" in result.content for result in results)
