"""Structured stops shared by the offline capture pipeline."""

from typing import Any, Dict, Optional


class PipelineStop(Exception):
    """A deterministic, user-actionable stop rather than an untyped failure."""

    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def as_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }

