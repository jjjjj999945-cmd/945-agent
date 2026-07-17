class LLMError(Exception):
    code = "LLM_PROVIDER_ERROR"
    status_code = 503

    def __init__(
        self,
        message: str,
        *,
        request_id: str | None = None,
        provider_request_id: str | None = None,
        http_attempts: int = 0,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.request_id = request_id
        self.provider_request_id = provider_request_id
        self.http_attempts = http_attempts

    def attach_request_id(self, request_id: str) -> "LLMError":
        if self.request_id is None:
            self.request_id = request_id
        return self


class LLMConfigError(LLMError):
    code = "LLM_CONFIG_ERROR"


class LLMTimeoutError(LLMError):
    code = "LLM_TIMEOUT"


class LLMRateLimitedError(LLMError):
    code = "LLM_RATE_LIMITED"


class LLMProviderError(LLMError):
    code = "LLM_PROVIDER_ERROR"


class LLMOutputInvalidError(LLMError):
    code = "LLM_OUTPUT_INVALID"
    status_code = 502
