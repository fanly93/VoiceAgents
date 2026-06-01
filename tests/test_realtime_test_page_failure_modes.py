import shutil
import subprocess
from pathlib import Path

import pytest


STATIC_PAGE = Path("voiceagents/api/static/realtime-test.html")


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required for browser JS harness")
def test_realtime_test_page_failure_modes_and_reconnect_are_clean() -> None:
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

const clientSecretPayload = () => ({
  provider: "openai_realtime",
  model: "gpt-realtime-2",
  client_secret: "ephemeral-secret-for-test",
  tool_call_token: "tool-token-for-test",
  connection_url: "https://api.openai.test/v1/realtime/calls",
  session_config: {
    tools: [{ name: "query_product_knowledge" }],
  },
});

const settle = async () => {
  for (let i = 0; i < 8; i += 1) {
    await new Promise((resolve) => setImmediate(resolve));
  }
};

function makeHarness(options = {}) {
  const elements = new Map();
  const createdPeerConnections = [];
  const createdTracks = [];
  const createdAudios = [];
  const fetchCalls = [];
  let getUserMediaCalls = 0;

  class FakeElement {
    constructor(id) {
      this.id = id;
      this.textContent = "";
      this.disabled = false;
      this.value = id === "response-mode" ? "text" : "";
      this.listeners = {};
      this.attributes = {};
      this.classList = {
        values: new Set(),
        toggle: (name, enabled) => {
          if (enabled) {
            this.classList.values.add(name);
          } else {
            this.classList.values.delete(name);
          }
        },
      };
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
    dispatch(name) {
      for (const callback of this.listeners[name] || []) {
        callback({ target: this });
      }
    }
  }

  const document = {
    body: {
      appended: [],
      appendChild: (node) => {
        document.body.appended.push(node);
      },
    },
    getElementById: (id) => {
      if (!elements.has(id)) {
        elements.set(id, new FakeElement(id));
      }
      return elements.get(id);
    },
  };

  const makeTrack = () => {
    const track = {
      enabled: true,
      stopped: false,
      stop() {
        this.stopped = true;
      },
    };
    createdTracks.push(track);
    return track;
  };

  const makeStream = () => {
    const track = makeTrack();
    return {
      getTracks: () => [track],
      getAudioTracks: () => [track],
    };
  };

  class FakeDataChannel {
    constructor() {
      this.readyState = "open";
      this.listeners = {};
      this.sent = [];
      this.closed = false;
    }
    addEventListener(name, callback) {
      this.listeners[name] = this.listeners[name] || [];
      this.listeners[name].push(callback);
    }
    dispatch(name, event = {}) {
      for (const callback of this.listeners[name] || []) {
        callback(event);
      }
    }
    send(payload) {
      this.sent.push(payload);
    }
    close() {
      this.closed = true;
      this.readyState = "closed";
    }
  }

  class FakePeerConnection {
    constructor() {
      this.closed = false;
      this.dataChannel = null;
      this.localDescription = null;
      this.remoteDescription = null;
      createdPeerConnections.push(this);
    }
    addTrack() {}
    createDataChannel() {
      this.dataChannel = new FakeDataChannel();
      return this.dataChannel;
    }
    async createOffer() {
      return { sdp: "offer-sdp" };
    }
    async setLocalDescription(offer) {
      this.localDescription = offer;
    }
    async setRemoteDescription(answer) {
      this.remoteDescription = answer;
    }
    close() {
      this.closed = true;
    }
  }

  class FakeAudio {
    constructor() {
      this.autoplay = false;
      this.style = {};
      this.paused = false;
      this.removed = false;
      this.srcObject = "initial";
      createdAudios.push(this);
    }
    pause() {
      this.paused = true;
    }
    remove() {
      this.removed = true;
    }
  }

  const context = {
    window: {
      voiceAgentsOpenAIRealtimeAdapter: {
        normalizeOpenAIRealtimeEvent: () => null,
        sendOpenAIResponseCreate: () => {},
        sendOpenAIToolResult: () => {},
      },
    },
    document,
    navigator: {
      language: "zh-CN",
      mediaDevices: {
        getUserMedia: async () => {
          getUserMediaCalls += 1;
          if (options.getUserMediaRejects) {
            throw new Error("NotAllowedError");
          }
          return makeStream();
        },
      },
    },
    crypto: {
      _count: 0,
      randomUUID() {
        this._count += 1;
        return `uuid-${this._count}`;
      },
    },
    performance: {
      now: () => 100,
    },
    fetch: async (url, request = {}) => {
      fetchCalls.push({ url: String(url), request });
      if (String(url) === "/v1/realtime/validation-scenarios") {
        return response({ json: [] });
      }
      if (options.fetch) {
        return options.fetch(String(url), request, fetchCalls.length);
      }
      if (String(url) === "/v1/realtime/client-secret") {
        return response({ json: clientSecretPayload() });
      }
      return response({ text: "answer-sdp" });
    },
    RTCPeerConnection: FakePeerConnection,
    RTCSessionDescription: class {
      constructor(value) {
        Object.assign(this, value);
      }
    },
    Audio: FakeAudio,
    console,
  };
  context.window.window = context.window;
  vm.createContext(context);
  vm.runInContext(inline[1], context);

  return {
    context,
    elements,
    fetchCalls,
    createdPeerConnections,
    createdTracks,
    createdAudios,
    getUserMediaCalls: () => getUserMediaCalls,
    panel: (id) => elements.get(id).textContent,
    click: async (id) => {
      elements.get(id).click();
      await settle();
    },
    debug: () => context.window.voiceAgentsRealtimeTest.getDebugState(),
  };
}

(async () => {
  {
    const harness = makeHarness({
      fetch: async (url) => {
        assert(url === "/v1/realtime/client-secret", "client-secret failure should not call SDP endpoint");
        return response({ ok: false, status: 503, text: "missing API key" });
      },
    });
    await harness.click("start-session");
    assert(harness.panel("session-state") === "error 503", "client-secret failure should show HTTP error");
    assert(harness.panel("provider-events").includes("missing API key"), "client-secret failure should show safe provider detail");
    assert(harness.getUserMediaCalls() === 0, "client-secret failure should not request microphone");
    assert(harness.createdPeerConnections.length === 0, "client-secret failure should not create peer connection");
    const debug = harness.debug();
    assert(!debug.hasClientSecret, "client-secret failure should not retain client secret");
    assert(!debug.hasLocalStream, "client-secret failure should not retain local stream");
    assert(!debug.hasRemoteAudio, "client-secret failure should not retain remote audio");
  }

    {
      const harness = makeHarness({ getUserMediaRejects: true });
      await harness.click("start-session");
      assert(harness.panel("session-state") === "error", "permission denial should show generic error state");
    assert(
      !harness.fetchCalls.some((call) => call.url === "https://api.openai.test/v1/realtime/calls"),
      "permission denial should not call OpenAI SDP endpoint",
    );
      const debug = harness.debug();
      assert(!debug.hasClientSecret, "permission denial should clear client secret");
      assert(!debug.hasPeerConnection, "permission denial should not retain peer connection");
      assert(!debug.hasLocalStream, "permission denial should not retain local stream");
    }

  {
    const harness = makeHarness({
      fetch: async (url) => {
        if (url === "/v1/realtime/client-secret") {
          return response({ json: clientSecretPayload() });
        }
        return response({ ok: false, status: 502, text: "bad gateway" });
      },
    });
    await harness.click("start-session");
    assert(harness.panel("session-state") === "error", "SDP failure should show error state");
    assert(harness.panel("provider-events").includes("OpenAI SDP exchange failed: 502"), "SDP failure should show safe error");
    assert(harness.createdPeerConnections[0].closed, "SDP failure should close peer connection");
    assert(harness.createdTracks[0].stopped, "SDP failure should stop local track");
    assert(harness.createdAudios[0].paused && harness.createdAudios[0].removed, "SDP failure should remove remote audio");
    const debug = harness.debug();
    assert(!debug.hasClientSecret, "SDP failure should clear client secret");
    assert(!debug.hasPeerConnection, "SDP failure should clear peer connection");
    assert(!debug.hasLocalStream, "SDP failure should clear local stream");
    assert(!debug.hasRemoteAudio, "SDP failure should clear remote audio");
  }

  {
    const harness = makeHarness();
    await harness.click("start-session");
    const channel = harness.createdPeerConnections[0].dataChannel;
    channel.dispatch("close");
    assert(harness.panel("session-state") === "data_channel_closed", "data channel close should update state");
    channel.dispatch("error");
    assert(harness.panel("session-state") === "data_channel_error", "data channel error should update state");
  }

  {
    let firstSdpAttempt = true;
    const sessionIds = [];
    const harness = makeHarness({
      fetch: async (url, request) => {
        if (url === "/v1/realtime/client-secret") {
          sessionIds.push(JSON.parse(request.body).session_id);
          return response({ json: clientSecretPayload() });
        }
        if (firstSdpAttempt) {
          firstSdpAttempt = false;
          return response({ ok: false, status: 500, text: "first failure" });
        }
        return response({ text: "answer-sdp" });
      },
    });
    await harness.click("start-session");
    assert(harness.panel("session-state") === "error", "first failed start should end in error");
    await harness.click("start-session");
    assert(harness.panel("session-state") === "connected", "second start should reconnect");
    assert(sessionIds.length === 2 && sessionIds[0] !== sessionIds[1], "reconnect should allocate a fresh session id");
    assert(harness.createdPeerConnections.length === 2, "reconnect should allocate a fresh peer connection");
    assert(harness.createdPeerConnections[0].closed, "failed peer connection should be closed");
    assert(!harness.createdPeerConnections[1].closed, "reconnected peer connection should stay open");
    const debug = harness.debug();
    assert(debug.hasClientSecret, "connected session should retain current client secret");
    assert(debug.hasPeerConnection, "connected session should retain peer connection");
    assert(debug.hasLocalStream, "connected session should retain local stream");
    assert(debug.hasRemoteAudio, "connected session should retain remote audio");
  }
})();
"""
    result = subprocess.run(
        ["node", "-e", script, str(STATIC_PAGE)],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
