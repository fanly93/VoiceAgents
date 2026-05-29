#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_EXAMPLES_DIR = Path("examples/call-simulations")


def request_json(url: str, payload: dict | None = None) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    method = "GET"

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with HTTP {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"{method} {url} failed: {error.reason}") from error


def load_examples(examples_dir: Path) -> list[tuple[Path, dict]]:
    paths = sorted(examples_dir.glob("*.json"))
    if not paths:
        raise RuntimeError(f"No example payloads found in {examples_dir}")

    examples = []
    for path in paths:
        examples.append((path, json.loads(path.read_text())))
    return examples


def run_smoke(base_url: str, examples_dir: Path) -> None:
    base_url = base_url.rstrip("/")

    health = request_json(f"{base_url}/health")
    if health != {"status": "ok"}:
        raise RuntimeError(f"Unexpected health response: {health}")
    print("health: ok")

    for path, payload in load_examples(examples_dir):
        body = request_json(f"{base_url}/v1/calls/simulate", payload)
        if "response_text" not in body or "tools_called" not in body:
            raise RuntimeError(f"{path.name} returned an unexpected response: {body}")

        outcome = "handoff" if body.get("handoff_required") else "resolved"
        tools = ",".join(body.get("tools_called", []))
        print(f"{path.name}: {outcome} tools={tools}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test a running VoiceAgents API server.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--examples-dir", type=Path, default=DEFAULT_EXAMPLES_DIR)
    args = parser.parse_args()

    try:
        run_smoke(args.base_url, args.examples_dir)
    except RuntimeError as error:
        print(f"smoke failed: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
