from __future__ import annotations

from typing import Any


class ToolError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def failure(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    safe_details = details or {}
    return {
        "ok": False,
        "error": f"{code}: {message}",
        "error_info": {
            "code": code,
            "message": message,
            "details": safe_details,
        },
        "warnings": [],
    }
