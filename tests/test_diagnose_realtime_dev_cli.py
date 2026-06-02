import importlib.util
from pathlib import Path


def load_script_module():
    path = Path("scripts/diagnose_realtime_dev.py")
    spec = importlib.util.spec_from_file_location("diagnose_realtime_dev", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_realtime_diagnostics_script_prints_safe_pass_output(capsys) -> None:
    module = load_script_module()

    def fake_request_json(url: str) -> dict:
        if url.endswith("/health"):
            return {"status": "ok"}
        if url.endswith("/v1/realtime/dev-diagnostics"):
            return {
                "overall_status": "pass",
                "provider": "mock",
                "checks": [
                    {
                        "name": "provider_supported",
                        "status": "pass",
                        "summary": "Realtime provider 'mock' is supported.",
                        "detail": "safe",
                        "remediation": "No action needed.",
                    }
                ],
            }
        raise AssertionError(url)

    result = module.run_diagnostics("http://127.0.0.1:8000", request_json_fn=fake_request_json)

    output = capsys.readouterr().out
    assert result == 0
    assert "health: ok" in output
    assert "overall: pass provider=mock" in output
    assert "provider_supported: pass" in output


def test_realtime_diagnostics_script_returns_nonzero_on_fail(capsys) -> None:
    module = load_script_module()

    def fake_request_json(url: str) -> dict:
        if url.endswith("/health"):
            return {"status": "ok"}
        if url.endswith("/v1/realtime/dev-diagnostics"):
            return {
                "overall_status": "fail",
                "provider": "openai_realtime",
                "checks": [
                    {
                        "name": "openai_api_key",
                        "status": "fail",
                        "summary": "OPENAI_API_KEY is missing.",
                        "detail": "missing",
                        "remediation": "Set OPENAI_API_KEY in the local server environment.",
                    }
                ],
            }
        raise AssertionError(url)

    result = module.run_diagnostics("http://127.0.0.1:8000", request_json_fn=fake_request_json)

    output = capsys.readouterr().out
    assert result == 1
    assert "overall: fail provider=openai_realtime" in output
    assert "openai_api_key: fail" in output
    assert "Set OPENAI_API_KEY" in output


def test_realtime_diagnostics_script_does_not_print_secret_values(capsys) -> None:
    module = load_script_module()

    def fake_request_json(url: str) -> dict:
        if url.endswith("/health"):
            return {"status": "ok"}
        if url.endswith("/v1/realtime/dev-diagnostics"):
            return {
                "overall_status": "pass",
                "provider": "openai_realtime",
                "checks": [
                    {
                        "name": "openai_api_key",
                        "status": "pass",
                        "summary": "OPENAI_API_KEY is configured on the server.",
                        "detail": "configured",
                        "remediation": "No action needed.",
                    }
                ],
            }
        raise AssertionError(url)

    result = module.run_diagnostics("http://127.0.0.1:8000", request_json_fn=fake_request_json)

    output = capsys.readouterr().out
    assert result == 0
    assert "sk-" not in output
    assert "client_secret" not in output
    assert "tool_call_token" not in output

