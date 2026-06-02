from voiceagents.realtime.diagnostics import build_realtime_dev_diagnostics


def check_by_name(diagnostics, name: str):
    return next(check for check in diagnostics.checks if check.name == name)


def test_mock_provider_diagnostics_pass_without_openai_key() -> None:
    diagnostics = build_realtime_dev_diagnostics(
        {
            "VOICEAGENTS_REALTIME_PROVIDER": "mock",
            "VOICEAGENTS_TRANSCRIPT_LOGGING": "structured",
        }
    )

    assert diagnostics.overall_status == "pass"
    assert diagnostics.provider == "mock"
    assert check_by_name(diagnostics, "provider_supported").status == "pass"
    assert check_by_name(diagnostics, "provider_model").status == "pass"
    assert "openai_api_key" not in {check.name for check in diagnostics.checks}


def test_unsupported_provider_diagnostics_fail_with_remediation() -> None:
    diagnostics = build_realtime_dev_diagnostics(
        {"VOICEAGENTS_REALTIME_PROVIDER": "unknown_provider"}
    )

    assert diagnostics.overall_status == "fail"
    check = check_by_name(diagnostics, "provider_supported")
    assert check.status == "fail"
    assert "mock" in check.remediation
    assert "openai_realtime" in check.remediation
    assert "dashscope_realtime" in check.remediation


def test_dashscope_diagnostics_use_registry_without_openai_checks() -> None:
    diagnostics = build_realtime_dev_diagnostics(
        {"VOICEAGENTS_REALTIME_PROVIDER": "dashscope_realtime"}
    )

    check_names = {check.name for check in diagnostics.checks}
    assert diagnostics.provider == "dashscope_realtime"
    assert check_by_name(diagnostics, "provider_supported").status == "pass"
    assert check_by_name(diagnostics, "provider_model").status == "pass"
    assert "openai_model" not in check_names
    assert "openai_api_key" not in check_names


def test_openai_diagnostics_fail_when_dev_gate_is_disabled() -> None:
    diagnostics = build_realtime_dev_diagnostics(
        {
            "VOICEAGENTS_REALTIME_PROVIDER": "openai_realtime",
            "OPENAI_API_KEY": "sk-test-secret",
        }
    )

    assert diagnostics.overall_status == "fail"
    assert check_by_name(diagnostics, "openai_dev_gate").status == "fail"
    assert check_by_name(diagnostics, "openai_api_key").status == "pass"
    assert "sk-test-secret" not in diagnostics.model_dump_json()


def test_openai_diagnostics_fail_when_api_key_is_missing() -> None:
    diagnostics = build_realtime_dev_diagnostics(
        {
            "VOICEAGENTS_REALTIME_PROVIDER": "openai_realtime",
            "VOICEAGENTS_ENABLE_REALTIME_DEV_ENDPOINTS": "true",
        }
    )

    assert diagnostics.overall_status == "fail"
    check = check_by_name(diagnostics, "openai_api_key")
    assert check.status == "fail"
    assert "OPENAI_API_KEY" in check.remediation


def test_diagnostics_warn_for_invalid_optional_realtime_config() -> None:
    diagnostics = build_realtime_dev_diagnostics(
        {
            "VOICEAGENTS_REALTIME_PROVIDER": "mock",
            "VOICEAGENTS_TRANSCRIPT_LOGGING": "verbatim",
            "VOICEAGENTS_REALTIME_CLIENT_SECRET_RATE_LIMIT": "many",
        }
    )

    assert diagnostics.overall_status == "warn"
    assert check_by_name(diagnostics, "transcript_logging").status == "warn"
    assert check_by_name(diagnostics, "client_secret_rate_limit").status == "warn"
