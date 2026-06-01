import shutil
import subprocess
from pathlib import Path

import pytest


STATIC_PAGE = Path("voiceagents/api/static/realtime-test.html")


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required for browser JS harness")
def test_page_loads_validation_scenarios() -> None:
    run_validation_flow_harness()


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required for browser JS harness")
def test_page_starts_validation_run() -> None:
    run_validation_flow_harness()


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required for browser JS harness")
def test_page_finishes_validation_run_with_safe_observation() -> None:
    run_validation_flow_harness()


def run_validation_flow_harness() -> None:
    script = r"""
const fs = require("fs");
const vm = require("vm");

const html = fs.readFileSync(process.argv[1], "utf8");
const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
const inline = scripts.find((match) => match[1].includes("const state ="));
if (!inline) {
  throw new Error("inline realtime script not found");
}

const assert = (condition, message) => {
  if (!condition) {
    throw new Error(message);
  }
};

const response = ({ ok = true, status = 200, json = {}, text = "" }) => ({
  ok,
  status,
  json: async () => json,
  text: async () => text,
});

const settle = async () => {
  for (let i = 0; i < 8; i += 1) {
    await new Promise((resolve) => setImmediate(resolve));
  }
};

const elements = new Map();
const fetchCalls = [];

class FakeElement {
  constructor(id) {
    this.id = id;
    this.textContent = "";
    this.disabled = false;
    this.checked = false;
    this.value = id === "response-mode" ? "text" : "";
    this.listeners = {};
    this.options = [];
    this.attributes = {};
    this.classList = { toggle: () => {} };
  }
  addEventListener(name, callback) {
    this.listeners[name] = this.listeners[name] || [];
    this.listeners[name].push(callback);
  }
  setAttribute(name, value) {
    this.attributes[name] = value;
  }
  appendChild(option) {
    this.options.push(option);
    if (!this.value) {
      this.value = option.value;
    }
  }
  click() {
    for (const callback of this.listeners.click || []) {
      callback({ target: this });
    }
  }
}

const document = {
  body: { appendChild: () => {} },
  createElement: (tagName) => ({ tagName, value: "", textContent: "" }),
  getElementById: (id) => {
    if (!elements.has(id)) {
      elements.set(id, new FakeElement(id));
    }
    return elements.get(id);
  },
};

const context = {
  window: {
    voiceAgentsOpenAIRealtimeAdapter: {
      normalizeOpenAIRealtimeEvent: () => null,
      sendOpenAIResponseCreate: () => {},
      sendOpenAIToolResult: () => {},
    },
  },
  document,
  navigator: { language: "zh-CN", mediaDevices: { getUserMedia: async () => ({}) } },
  crypto: { randomUUID: () => "uuid-1" },
  performance: { now: () => 100 },
  fetch: async (url, request = {}) => {
    fetchCalls.push({ url: String(url), request });
    if (String(url) === "/v1/realtime/validation-scenarios") {
      return response({
        json: [
          {
            scenario_id: "order_status",
            label: "Order status lookup",
            suggested_prompt: "Please check order ORD-20260601-1842.",
          },
        ],
      });
    }
    if (String(url) === "/v1/realtime/validation-runs") {
      return response({
        json: {
          run_id: "vrun-20260601-120000-abcdef12",
          summary_path: ".voiceagents/validation-runs/vrun-20260601-120000-abcdef12/summary.json",
          report_path: ".voiceagents/validation-runs/vrun-20260601-120000-abcdef12/report.md",
        },
      });
    }
    if (String(url).endsWith("/finish")) {
      return response({
        json: {
          run_id: "vrun-20260601-120000-abcdef12",
          status: "pass",
          report_path: ".voiceagents/validation-runs/vrun-20260601-120000-abcdef12/report.md",
          checks: [],
        },
      });
    }
    return response({});
  },
  RTCPeerConnection: class {},
  RTCSessionDescription: class {},
  Audio: class {},
  console,
};
context.window.window = context.window;
vm.createContext(context);
vm.runInContext(inline[1], context);

(async () => {
  const api = context.window.voiceAgentsRealtimeTest;
  await api.loadValidationScenarios();
  assert(elements.get("validation-scenario").value === "order_status", "scenario selector should load API scenario");

  context.window.voiceAgentsRealtimeTest.setDebugSession({
    sessionId: "session-123",
    callId: "call-123",
    provider: "mock",
  });
  document.getElementById("validation-heard-voice").checked = true;
  document.getElementById("validation-voice-quality").checked = true;
  document.getElementById("validation-business-answer").checked = true;
  document.getElementById("validation-demo-ready").checked = true;
  document.getElementById("validation-notes").value = "clear enough";
  document.getElementById("session-state").textContent = "ended";
  document.getElementById("transcript").textContent = "Where is ORD-20260601-1842?";
  document.getElementById("assistant-response").textContent = "Order has been paid.";
  document.getElementById("tool-calls").textContent = "lookup_order: Order has been paid.";
  document.getElementById("handoff-state").textContent = "none";
  document.getElementById("provider-events").textContent = "data_channel=open";
  document.getElementById("latency").textContent = "120 ms";

  await api.startValidationRun();
  await api.finishValidationRun();

  const finishCall = fetchCalls.find((call) => call.url.endsWith("/finish"));
  assert(finishCall, "finish endpoint should be called");
  const finishBody = JSON.parse(finishCall.request.body);
  assert(finishBody.tool_names[0] === "lookup_order", "tool name should be parsed from panel");
  assert(finishBody.manual_assertions.heard_voice === true, "manual assertion should be captured");
  assert(!JSON.stringify(finishBody).includes("client_secret"), "finish payload should not include secrets");
  assert(elements.get("validation-result").textContent.includes("pass"), "saved status should render");
})();
"""
    result = subprocess.run(
        ["node", "-e", script, str(STATIC_PAGE)],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
