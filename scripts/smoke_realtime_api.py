#!/usr/bin/env python3
import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://127.0.0.1:8767"


def request_json(
    url: str,
    payload: dict | None = None,
    *,
    headers: dict[str, str] | None = None,
    expect_status: int = 200,
) -> dict:
    data = None
    request_headers = {"Accept": "application/json"} | (headers or {})
    method = "GET"

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
        method = "POST"

    request = Request(url, data=data, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            body = _decode_json(response.read())
            if response.status != expect_status:
                raise RuntimeError(
                    f"{method} {url} returned HTTP {response.status}, expected {expect_status}: {body}"
                )
            return body
    except HTTPError as error:
        body = _decode_json(error.read())
        if error.code == expect_status:
            return body
        raise RuntimeError(
            f"{method} {url} failed with HTTP {error.code}, expected {expect_status}: {body}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"{method} {url} failed: {error.reason}") from error


def _decode_json(raw: bytes) -> dict:
    text = raw.decode("utf-8", errors="replace")
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


def run_smoke(base_url: str) -> None:
    base_url = base_url.rstrip("/")

    health = request_json(f"{base_url}/health")
    if health != {"status": "ok"}:
        raise RuntimeError(f"Unexpected health response: {health}")
    print("health: ok")

    client_secret = request_json(
        f"{base_url}/v1/realtime/client-secret",
        {
            "session_id": "session-smoke",
            "call_id": "call-smoke",
            "merchant_id": "merchant-demo",
            "response_mode": "text",
            "locale": "en-US",
            "safety_subject_id": "smoke_subject",
        },
    )
    token = client_secret.get("tool_call_token")
    if not token:
        raise RuntimeError("client-secret response did not include tool_call_token")
    if "OPENAI_API_KEY" in json.dumps(client_secret):
        raise RuntimeError("client-secret response leaked OPENAI_API_KEY marker")
    print(f"client-secret: provider={client_secret.get('provider')} model={client_secret.get('model')}")

    tool_calls = [
        ("lookup_order", {"order_id": "ORDER-REDACTED-001"}),
        ("lookup_logistics", {"order_id": "ORDER-REDACTED-001"}),
        ("query_product_knowledge", {"query": "How should I wash this wig?", "locale": "en-US"}),
        (
            "handoff_to_human",
            {
                "reason": "customer_requests_human",
                "summary": "Customer asked for a person.",
            },
        ),
    ]
    for tool_name, arguments in tool_calls:
        body = request_json(
            f"{base_url}/v1/realtime/tool-call",
            {
                "session_id": "session-smoke",
                "call_id": "call-smoke",
                "merchant_id": "merchant-demo",
                "tool_name": tool_name,
                "arguments": arguments,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        if body.get("tool_name") != tool_name:
            raise RuntimeError(f"{tool_name} returned unexpected response: {body}")
        print(f"{tool_name}: ok={body.get('ok')} handoff={body.get('handoff_required')}")

    request_json(
        f"{base_url}/v1/realtime/tool-call",
        {
            "session_id": "session-smoke",
            "call_id": "call-smoke",
            "merchant_id": "merchant-demo",
            "tool_name": "lookup_order",
            "arguments": {"order_id": "ORDER-REDACTED-001"},
        },
        expect_status=401,
    )
    print("missing authorization: rejected")

    request_json(
        f"{base_url}/v1/realtime/tool-call",
        {
            "session_id": "session-smoke",
            "call_id": "call-smoke",
            "merchant_id": "merchant-demo",
            "tool_name": "run_shell",
            "arguments": {},
        },
        headers={"Authorization": f"Bearer {token}"},
        expect_status=400,
    )
    print("unknown tool: rejected")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke-test realtime VoiceAgents API endpoints in mock provider mode."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    try:
        run_smoke(args.base_url)
    except RuntimeError as error:
        print(f"realtime smoke failed: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
