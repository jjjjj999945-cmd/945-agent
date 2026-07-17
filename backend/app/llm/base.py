from typing import Protocol, runtime_checkable

from backend.app.llm.models import AgentModelRequest, AgentModelResponse


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    async def generate(self, request: AgentModelRequest) -> AgentModelResponse:
        raise NotImplementedError
