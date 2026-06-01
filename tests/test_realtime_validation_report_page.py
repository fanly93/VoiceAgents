import shutil
import subprocess
from pathlib import Path

import pytest


STATIC_PAGE = Path("voiceagents/api/static/realtime-validation-reports.html")


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required for browser JS harness")
def test_load_runs_renders_empty_state() -> None:
    run_report_harness(
        r"""
  await api.loadRuns();

  assert(fetchCalls[0].url === "/v1/realtime/validation-report-runs", "run list endpoint should be fetched");
  assert(document.getElementById("empty-state").classList.hidden === false, "empty state should be visible");
  assert(document.getElementById("error-state").classList.hidden === true, "error state should stay hidden");
  assert(document.getElementById("run-list").children.length === 0, "run list should be empty");
"""
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required for browser JS harness")
def test_load_runs_renders_error_state() -> None:
    run_report_harness(
        r"""
  fetchMode = "error";
  await api.loadRuns();

  assert(document.getElementById("error-state").classList.hidden === false, "error state should be visible");
  assert(document.getElementById("empty-state").classList.hidden === true, "empty state should be hidden");
"""
    )


def run_report_harness(assertions: str) -> None:
    script = (
        r"""
const fs = require("fs");
const vm = require("vm");

const html = fs.readFileSync(process.argv[1], "utf8");
const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
const inline = scripts.find((match) => match[1].includes("const state ="));
if (!inline) {
  throw new Error("inline validation report script not found");
}

const assert = (condition, message) => {
  if (!condition) {
    throw new Error(message);
  }
};

const response = ({ ok = true, status = 200, json = [] }) => ({
  ok,
  status,
  json: async () => json,
});

const elements = new Map();
const fetchCalls = [];
let fetchMode = "empty";

class FakeClassList {
  constructor() {
    this.hidden = false;
  }
  toggle(name, enabled) {
    if (name === "hidden") {
      this.hidden = Boolean(enabled);
    }
  }
  add(name) {
    if (name === "hidden") {
      this.hidden = true;
    }
  }
  remove(name) {
    if (name === "hidden") {
      this.hidden = false;
    }
  }
}

class FakeElement {
  constructor(id) {
    this.id = id;
    this.textContent = "";
    this.value = "";
    this.children = [];
    this.listeners = {};
    this.attributes = {};
    this.className = "";
    this.classList = new FakeClassList();
  }
  appendChild(child) {
    this.children.push(child);
    return child;
  }
  replaceChildren(...children) {
    this.children = children;
  }
  addEventListener(name, callback) {
    this.listeners[name] = this.listeners[name] || [];
    this.listeners[name].push(callback);
  }
  setAttribute(name, value) {
    this.attributes[name] = value;
  }
  click() {
    for (const callback of this.listeners.click || []) {
      callback({ target: this });
    }
  }
}

const document = {
  createElement: (tagName) => new FakeElement(tagName),
  getElementById: (id) => {
    if (!elements.has(id)) {
      elements.set(id, new FakeElement(id));
    }
    return elements.get(id);
  },
};

const context = {
  window: {},
  document,
  navigator: { clipboard: { writeText: async () => {} } },
  fetch: async (url) => {
    fetchCalls.push({ url: String(url) });
    if (fetchMode === "error") {
      return response({ ok: false, status: 500 });
    }
    return response({ json: [] });
  },
  console,
};
context.window.window = context.window;
vm.createContext(context);
vm.runInContext(inline[1], context);

(async () => {
  const api = context.window.voiceAgentsValidationReports;
"""
        + assertions
        + r"""
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
"""
    )
    result = subprocess.run(
        ["node", "-e", script, str(STATIC_PAGE)],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
