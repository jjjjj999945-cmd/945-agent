from typing import Any


def ok(data: Any) -> dict[str, Any]:
    return {
        "data": data,
        "error": None
    }


def error(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        }
    }
