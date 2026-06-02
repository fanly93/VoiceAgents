#!/usr/bin/env python3
import argparse
import json
import sys
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def request_json(url: str) -> dict:
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=10) as response:
            return _decode_json(response.read())
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GET {url} failed with HTTP {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"GET {url} failed: {error.reason}") from error


def run_diagnostics(
    base_url: str,
    *,
    request_json_fn: Callable[[str], dict] = request_json,
) -> int:
    base_url = base_url.rstrip("/")

    health = request_json_fn(f"{base_url}/health")
    if health != {"status": "ok"}:
        raise RuntimeError(f"Unexpected health response: {health}")
    print("health: ok")

    diagnostics = request_json_fn(f"{base_url}/v1/realtime/dev-diagnostics")
    overall_status = diagnostics.get("overall_status", "fail")
    provider = diagnostics.get("provider", "unknown")
    print(f"overall: {overall_status} provider={provider}")

    for check in diagnostics.get("checks", []):
        name = check.get("name", "unknown")
        status = check.get("status", "fail")
        summary = check.get("summary", "")
        remediation = check.get("remediation", "")
        print(f"{name}: {status} - {summary}")
        if remediation and remediation != "No action needed.":
            print(f"  fix: {remediation}")

    return 1 if overall_status == "fail" else 0


def _decode_json(raw: bytes) -> dict:
    text = raw.decode("utf-8", errors="replace")
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Response was not JSON: {text[:200]}") from error
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Response JSON was not an object: {parsed}")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diagnose a running local VoiceAgents realtime development server."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    try:
        return run_diagnostics(args.base_url)
    except RuntimeError as error:
        print(f"realtime diagnostics failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

