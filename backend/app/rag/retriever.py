from pydantic import BaseModel, ConfigDict


class KnowledgeChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    metadata: dict[str, str]


KNOWLEDGE_BASE = [
    KnowledgeChunk(
        content="深蹲动作要点：保持核心收紧，髋和膝同步屈伸，膝盖方向跟随脚尖，避免疼痛情况下继续加重量。",
        metadata={
            "source_type": "exercise_knowledge",
            "topic": "squat",
            "locale": "zh-CN",
            "risk_level": "normal",
            "updated_at": "2026-07-17"
        }
    ),
    KnowledgeChunk(
        content="卧推动作要点：肩胛稳定，手腕中立，下降过程控制速度，胸肩疼痛时停止高强度训练。",
        metadata={
            "source_type": "exercise_knowledge",
            "topic": "bench_press",
            "locale": "zh-CN",
            "risk_level": "normal",
            "updated_at": "2026-07-17"
        }
    ),
    KnowledgeChunk(
        content="饮食估算规则：外食记录可以先估算份量和宏量营养，优先记录蛋白质、总热量和主要碳水来源。",
        metadata={
            "source_type": "nutrition_knowledge",
            "topic": "meal_estimation",
            "locale": "zh-CN",
            "risk_level": "normal",
            "updated_at": "2026-07-17"
        }
    ),
    KnowledgeChunk(
        content="945 产品规则：Agent 可以生成训练、饮食、打卡和计划调整草稿，但关键写入必须由用户确认后才保存。",
        metadata={
            "source_type": "product_rule",
            "topic": "confirmation_required",
            "locale": "zh-CN",
            "risk_level": "normal",
            "updated_at": "2026-07-17"
        }
    ),
    KnowledgeChunk(
        content="安全边界：胸闷、眩晕、晕厥、强烈疼痛、疑似受伤、心脏不适、极端节食和进食障碍倾向需要优先安全提醒。",
        metadata={
            "source_type": "safety_rule",
            "topic": "high_risk_inputs",
            "locale": "zh-CN",
            "risk_level": "high",
            "updated_at": "2026-07-17"
        }
    )
]


ALIASES = {
    "深蹲": ["深蹲", "squat", "髋", "膝"],
    "动作": ["动作", "训练", "exercise"],
    "蛋白质": ["蛋白质", "protein", "饮食", "外食", "估算", "宏量"],
    "确认": ["确认", "草稿", "保存", "写入", "confirmation"],
    "风险": ["胸闷", "眩晕", "疼痛", "安全", "risk"]
}


def _score(query: str, chunk: KnowledgeChunk) -> int:
    searchable = f"{chunk.content} {' '.join(chunk.metadata.values())}".lower()
    score = 0
    for token, aliases in ALIASES.items():
        if token in query or any(alias.lower() in query.lower() for alias in aliases):
            score += sum(1 for alias in aliases if alias.lower() in searchable)
    for raw_token in query.lower().split():
        if raw_token and raw_token in searchable:
            score += 1
    return score


def retrieve_knowledge(query: str, locale: str = "zh-CN", limit: int = 3) -> list[KnowledgeChunk]:
    candidates = [chunk for chunk in KNOWLEDGE_BASE if chunk.metadata["locale"] == locale]
    ranked = sorted(candidates, key=lambda chunk: _score(query, chunk), reverse=True)
    return [chunk for chunk in ranked if _score(query, chunk) > 0][:limit]
