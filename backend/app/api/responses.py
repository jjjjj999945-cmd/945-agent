from typing import Any


def ok(data: Any) -> dict[str, Any]:
    return {
        "data": data,
        "error": None
    }
