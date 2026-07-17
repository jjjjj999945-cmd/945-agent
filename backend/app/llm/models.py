from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.domain import Locale, RecordDraft, TodayResponseData


AgentIntent = Literal["safety_warning", "log_workout", "log_meal", "adjust_plan", "ask_question"]


class LLMModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConversationMessage(LLMModel):
    role: Literal["user", "assistant"]
    content: str


class AgentToolDefinition(LLMModel):
    name: str
    description: str
    parameters: dict[str, Any]

    def to_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "strict": True,
        }


class ToolCallProposal(LLMModel):
    call_id: str
    name: str
    arguments: dict[str, Any]


class ToolExecutionResult(LLMModel):
    call_id: str
    name: str
    output: Any
    record_draft: RecordDraft | None = None


class ProviderContinuation(LLMModel):
    output_items: list[dict[str, Any]]


class ProviderUsage(LLMModel):
    input_tokens: int = 0
    output_tokens: int = 0
    logical_generations: int = 0
    http_attempts: int = 0


class AgentModelRequest(LLMModel):
    request_id: str
    user_id: str
    locale: Locale
    message: str
    context: dict[str, Any] = Field(default_factory=dict)
    conversation: list[ConversationMessage] = Field(default_factory=list)
    today_context: TodayResponseData | None = None
    rag_chunks: list[dict[str, Any]] = Field(default_factory=list)
    tools: list[AgentToolDefinition] = Field(default_factory=list)
    continuation: ProviderContinuation | None = None
    tool_result: ToolExecutionResult | None = None


class AgentModelResponse(LLMModel):
    intent: AgentIntent
    reply: str
    provider: str
    model: str | None = None
    provider_request_id: str | None = None
    tool_call: ToolCallProposal | None = None
    record_draft: RecordDraft | None = None
    usage: ProviderUsage = Field(default_factory=ProviderUsage)
    degraded: bool = False
    degraded_reason: str | None = None
    continuation: ProviderContinuation | None = Field(default=None, exclude=True)
