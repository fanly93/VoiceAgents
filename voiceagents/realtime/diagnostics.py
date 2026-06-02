from collections.abc import Mapping
import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from voiceagents.realtime.contracts import RealtimeProviderName, TranscriptLoggingMode
from voiceagents.realtime.providers import (
    DEFAULT_OPENAI_REALTIME_MODEL,
    DEFAULT_OPENAI_REALTIME_VOICE,
)


DiagnosticsStatus = Literal["pass", "warn", "fail"]


class RealtimeDiagnosticsCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    status: DiagnosticsStatus
    summary: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    remediation: str = Field(min_length=1)


class RealtimeDevDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_status: DiagnosticsStatus
    provider: str = Field(min_length=1)
    checks: list[RealtimeDiagnosticsCheck]


def build_realtime_dev_diagnostics(
    env: Mapping[str, str] | None = None,
) -> RealtimeDevDiagnostics:
    source = env if env is not None else os.environ
    provider = source.get("VOICEAGENTS_REALTIME_PROVIDER", RealtimeProviderName.MOCK.value)
    checks = [_check_provider_supported(provider)]

    if provider == RealtimeProviderName.OPENAI_REALTIME.value:
        checks.extend(
            [
                _check_openai_dev_gate(source),
                _check_openai_api_key(source),
                _check_openai_model(source),
                _check_openai_voice(source),
            ]
        )
    else:
        checks.append(_pass_check("openai_model", "OpenAI model is not used in mock mode."))

    checks.extend(
        [
            _check_transcript_logging(source),
            _check_client_secret_rate_limit(source),
        ]
    )
    return RealtimeDevDiagnostics(
        overall_status=_overall_status(checks),
        provider=provider,
        checks=checks,
    )


def _check_provider_supported(provider: str) -> RealtimeDiagnosticsCheck:
    allowed = {item.value for item in RealtimeProviderName}
    if provider in allowed:
        return _pass_check(
            "provider_supported",
            f"Realtime provider '{provider}' is supported.",
        )
    return RealtimeDiagnosticsCheck(
        name="provider_supported",
        status="fail",
        summary="Realtime provider is not supported.",
        detail=f"Configured provider is '{provider}'.",
        remediation="Set VOICEAGENTS_REALTIME_PROVIDER to mock or openai_realtime.",
    )


def _check_openai_dev_gate(env: Mapping[str, str]) -> RealtimeDiagnosticsCheck:
    enabled = env.get("VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS", "false").lower() == "true"
    if enabled:
        return _pass_check(
            "openai_dev_gate",
            "OpenAI realtime dev endpoints are enabled for local development.",
        )
    return RealtimeDiagnosticsCheck(
        name="openai_dev_gate",
        status="fail",
        summary="OpenAI realtime dev endpoints are disabled.",
        detail="The app will reject real provider client-secret requests before calling OpenAI.",
        remediation="Set VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS=true only for local development.",
    )


def _check_openai_api_key(env: Mapping[str, str]) -> RealtimeDiagnosticsCheck:
    if env.get("OPENAI_API_KEY"):
        return _pass_check("openai_api_key", "OPENAI_API_KEY is configured on the server.")
    return RealtimeDiagnosticsCheck(
        name="openai_api_key",
        status="fail",
        summary="OPENAI_API_KEY is missing.",
        detail="OpenAI Realtime cannot mint an ephemeral client secret without a server-side API key.",
        remediation="Set OPENAI_API_KEY in the local server environment; never expose it to the browser.",
    )


def _check_openai_model(env: Mapping[str, str]) -> RealtimeDiagnosticsCheck:
    model = env.get("VOICEAGENTS_OPENAI_REALTIME_MODEL") or DEFAULT_OPENAI_REALTIME_MODEL
    return _pass_check("openai_model", f"OpenAI realtime model is configured as {model}.")


def _check_openai_voice(env: Mapping[str, str]) -> RealtimeDiagnosticsCheck:
    voice = env.get("VOICEAGENTS_OPENAI_REALTIME_VOICE") or DEFAULT_OPENAI_REALTIME_VOICE
    return _pass_check("openai_voice", f"OpenAI realtime voice is configured as {voice}.")


def _check_transcript_logging(env: Mapping[str, str]) -> RealtimeDiagnosticsCheck:
    value = env.get("VOICEAGENTS_TRANSCRIPT_LOGGING", TranscriptLoggingMode.STRUCTURED.value)
    try:
        TranscriptLoggingMode(value)
    except ValueError:
        return RealtimeDiagnosticsCheck(
            name="transcript_logging",
            status="warn",
            summary="Transcript logging mode is invalid.",
            detail=f"Configured VOICEAGENTS_TRANSCRIPT_LOGGING is '{value}'.",
            remediation="Use off, structured, or transcript. The API falls back to structured.",
        )
    return _pass_check("transcript_logging", f"Transcript logging mode is {value}.")


def _check_client_secret_rate_limit(env: Mapping[str, str]) -> RealtimeDiagnosticsCheck:
    value = env.get("VOICEAGENTS_REALTIME_CLIENT_SECRET_RATE_LIMIT")
    if value is None:
        return _pass_check("client_secret_rate_limit", "Client-secret rate limit uses the default.")
    try:
        if int(value) < 1:
            raise ValueError
    except ValueError:
        return RealtimeDiagnosticsCheck(
            name="client_secret_rate_limit",
            status="warn",
            summary="Client-secret rate limit is invalid.",
            detail=f"Configured VOICEAGENTS_REALTIME_CLIENT_SECRET_RATE_LIMIT is '{value}'.",
            remediation="Set VOICEAGENTS_REALTIME_CLIENT_SECRET_RATE_LIMIT to a positive integer.",
        )
    return _pass_check("client_secret_rate_limit", f"Client-secret rate limit is {value}.")


def _pass_check(name: str, summary: str) -> RealtimeDiagnosticsCheck:
    return RealtimeDiagnosticsCheck(
        name=name,
        status="pass",
        summary=summary,
        detail=summary,
        remediation="No action needed.",
    )


def _overall_status(checks: list[RealtimeDiagnosticsCheck]) -> DiagnosticsStatus:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "warn" for check in checks):
        return "warn"
    return "pass"

