(function () {
  function buildDashScopeProxyUrl(connectionUrl, token, origin) {
    if (!connectionUrl || !token) {
      throw new Error("DashScope proxy connection is not ready.");
    }
    const proxyUrl = new URL(connectionUrl, origin || window.location.origin);
    proxyUrl.protocol = proxyUrl.protocol === "https:" ? "wss:" : "ws:";
    proxyUrl.searchParams.set("token", token);
    return proxyUrl.toString();
  }

  function sendDashScopeControl(socket, action) {
    socket.send(JSON.stringify({ type: "control", payload: { action } }));
  }

  function sendDashScopeAudio(socket, frame) {
    socket.send(JSON.stringify({ type: "audio", payload: { frame } }));
  }

  function sendDashScopeToolResult(socket, payload) {
    socket.send(JSON.stringify({ type: "tool_result", payload }));
  }

  async function connectDashScopeRealtime(options) {
    const socket = new WebSocket(
      buildDashScopeProxyUrl(options.connectionUrl, options.token, options.origin),
    );
    await new Promise((resolve, reject) => {
      socket.addEventListener(
        "open",
        () => {
          if (options.isCurrent && !options.isCurrent()) {
            socket.close();
            reject(new Error("Realtime connection was replaced."));
            return;
          }
          if (options.onOpen) {
            options.onOpen(socket);
          }
          sendDashScopeControl(socket, "start");
          resolve();
        },
        { once: true },
      );
      socket.addEventListener(
        "error",
        () => {
          reject(new Error("DashScope proxy connection failed."));
        },
        { once: true },
      );
    });
    socket.addEventListener("close", () => {
      if (options.onClose) {
        options.onClose(socket);
      }
    });
    socket.addEventListener("message", (messageEvent) => {
      if (options.onMessage) {
        options.onMessage(messageEvent, socket);
      }
    });
    return socket;
  }

  window.voiceAgentsDashScopeRealtimeAdapter = {
    buildDashScopeProxyUrl,
    connectDashScopeRealtime,
    sendDashScopeControl,
    sendDashScopeAudio,
    sendDashScopeToolResult,
  };
})();
