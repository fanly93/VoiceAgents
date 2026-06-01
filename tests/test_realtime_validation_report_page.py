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


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required for browser JS harness")
def test_render_report_detail_loads_selected_run() -> None:
    run_report_harness(
        r"""
  fetchMode = "report";
  await api.loadRuns();

  assert(fetchCalls[1].url === "/v1/realtime/validation-report-runs/vrun-20260601-120000-abcdef12", "detail endpoint should be fetched");
  assert(document.getElementById("readiness-banner").textContent.includes("可以继续推进试点"), "readiness should render");
  assert(document.getElementById("scenario-coverage").children.length === 2, "scenario coverage should render");
  assert(flattenText(document.getElementById("business-proof")).includes("业务回答：通过"), "business proof should render");
  assert(flattenText(document.getElementById("audience-sections")).includes("老板"), "boss section should render");
  assert(flattenText(document.getElementById("audience-sections")).includes("客服主管"), "support lead section should render");
  assert(flattenText(document.getElementById("audience-sections")).includes("技术同事"), "technical section should render");
  assert(flattenText(document.getElementById("warnings")).includes("manual_business_confirmed"), "warnings should render");
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
const reportRun = {
  run_id: "vrun-20260601-120000-abcdef12",
  scenario_label: "Order status lookup",
  readiness: "ready_for_pilot",
  status: "pass",
  finished_at: "2026-06-01T12:01:00+00:00",
};
const reportDetail = {
  run_id: "vrun-20260601-120000-abcdef12",
  scenario: { scenario_id: "order_status", label: "Order status lookup" },
  status: "fail",
  readiness: "needs_another_validation",
  decision_summary: {
    label: "可以继续推进试点",
    summary: "订单状态查询场景验证结果为：可以继续推进试点。",
    next_action: "可把本摘要转发给决策人，进入试点准备。",
  },
  scenario_coverage: ["验证场景：订单状态查询", "预期工具：lookup_order"],
  business_proof: ["语音确认：通过", "业务回答：通过"],
  audience_sections: [
    { audience: "老板", title: "决策人摘要", bullets: ["结论：可以继续推进试点"] },
    { audience: "客服主管", title: "客服主管关注点", bullets: ["业务回答可接受"] },
    { audience: "技术同事", title: "技术复核点", bullets: ["检查项：9/10 通过"] },
  ],
  copy_summary: {
    text: "试点演示验证结果：订单状态查询，可以继续推进试点。\n证据：业务回答：通过。\n下一步：进入试点准备。",
  },
  checks: [],
  warnings: ["manual_business_confirmed: manual business/demo checks failed"],
};

const flattenText = (element) => {
  const childText = (element.children || []).map(flattenText).join(" ");
  return `${element.textContent || ""} ${childText}`.trim();
};

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
    if (fetchMode === "report" && String(url).endsWith("/vrun-20260601-120000-abcdef12")) {
      return response({ json: reportDetail });
    }
    if (fetchMode === "report") {
      return response({ json: [reportRun] });
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
