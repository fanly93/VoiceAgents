from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Generic, Mapping, Protocol, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class RedactionResult(Generic[T]):
    value: T
    redaction_applied: bool


class Redactor(Protocol):
    def redact_text(self, text: str) -> RedactionResult[str]:
        raise NotImplementedError

    def redact_mapping(self, data: Mapping[str, Any]) -> RedactionResult[dict[str, Any]]:
        raise NotImplementedError


class BasicTextRedactor:
    _EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    _PHONE_RE = re.compile(
        r"(?<!\w)(?:\+\d[\d\s().-]{7,}\d|\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4})(?!\w)"
    )
    _ORDER_RE = re.compile(
        r"\b(?:ORDER|ORD)[-_]?[A-Z0-9-]*\d[A-Z0-9-]*\b",
        re.IGNORECASE,
    )

    def redact_text(self, text: str) -> RedactionResult[str]:
        redacted = self._EMAIL_RE.sub("[EMAIL_REDACTED]", text)
        redacted = self._PHONE_RE.sub("[PHONE_REDACTED]", redacted)
        redacted = self._ORDER_RE.sub("[ORDER_REDACTED]", redacted)
        return RedactionResult(
            value=redacted,
            redaction_applied=redacted != text,
        )

    def redact_mapping(self, data: Mapping[str, Any]) -> RedactionResult[dict[str, Any]]:
        value, redaction_applied = self._redact_value(dict(data))
        return RedactionResult(
            value=value,
            redaction_applied=redaction_applied,
        )

    def _redact_value(self, value: Any) -> tuple[Any, bool]:
        if isinstance(value, str):
            result = self.redact_text(value)
            return result.value, result.redaction_applied

        if isinstance(value, Mapping):
            redaction_applied = False
            redacted: dict[str, Any] = {}
            for key, nested_value in value.items():
                nested_redacted, nested_applied = self._redact_value(nested_value)
                redacted[key] = nested_redacted
                redaction_applied = redaction_applied or nested_applied
            return redacted, redaction_applied

        if isinstance(value, list):
            redaction_applied = False
            redacted_items: list[Any] = []
            for item in value:
                redacted_item, item_applied = self._redact_value(item)
                redacted_items.append(redacted_item)
                redaction_applied = redaction_applied or item_applied
            return redacted_items, redaction_applied

        return value, False


_DEFAULT_REDACTOR = BasicTextRedactor()


def redact_text(text: str) -> RedactionResult[str]:
    return _DEFAULT_REDACTOR.redact_text(text)


def redact_mapping(data: Mapping[str, Any]) -> RedactionResult[dict[str, Any]]:
    return _DEFAULT_REDACTOR.redact_mapping(data)
