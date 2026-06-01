(function () {
  function textOrNull(value) {
    if (typeof value !== "string") {
      return null;
    }
    const text = value.trim();
    return text ? text : null;
  }

  function normalizeOpenAIRealtimeEvent(event) {
    if (!event || typeof event.type !== "string") {
      return null;
    }

    if (event.type === "session.created" || event.type === "session.updated") {
      return {
        event_type: "session.connected",
        state: "idle",
        provider_event_type: event.type,
      };
    }

    if (event.type === "response.output_audio_transcript.delta") {
      const text = textOrNull(event.delta);
      if (text === null) {
        return null;
      }
      return {
        event_type: "transcript.assistant.delta",
        state: "transcribing",
        speaker: "assistant",
        turn_id: event.item_id || event.response_id || null,
        sequence: event.content_index ?? event.output_index ?? null,
        text,
        provider_event_type: event.type,
      };
    }

    if (event.type === "response.output_text.delta") {
      const text = textOrNull(event.delta);
      if (text === null) {
        return null;
      }
      return {
        event_type: "transcript.assistant.delta",
        state: "transcribing",
        speaker: "assistant",
        turn_id: event.item_id || event.response_id || null,
        sequence: event.content_index ?? event.output_index ?? null,
        text,
        provider_event_type: event.type,
      };
    }

    if (event.type === "response.output_text.done") {
      const text = textOrNull(event.text);
      if (text === null) {
        return null;
      }
      return {
        event_type: "transcript.assistant.done",
        state: "transcribing",
        speaker: "assistant",
        turn_id: event.item_id || event.response_id || null,
        sequence: event.content_index ?? event.output_index ?? null,
        text,
        provider_event_type: event.type,
      };
    }

    if (event.type === "response.output_audio_transcript.done") {
      const text = textOrNull(event.transcript);
      if (text === null) {
        return null;
      }
      return {
        event_type: "transcript.assistant.done",
        state: "transcribing",
        speaker: "assistant",
        turn_id: event.item_id || event.response_id || null,
        sequence: event.content_index ?? event.output_index ?? null,
        text,
        provider_event_type: event.type,
      };
    }

    if (
      event.type === "conversation.item.input_audio_transcription.delta" ||
      event.type === "conversation.item.input_audio_transcription.segment"
    ) {
      const text = textOrNull(event.delta || event.text);
      if (text === null) {
        return null;
      }
      return {
        event_type: "transcript.user.delta",
        state: "transcribing",
        speaker: "user",
        turn_id: event.item_id || event.id || null,
        sequence: event.content_index ?? null,
        text,
        provider_event_type: event.type,
      };
    }

    if (event.type === "conversation.item.input_audio_transcription.completed") {
      const text = textOrNull(event.transcript);
      if (text === null) {
        return null;
      }
      return {
        event_type: "transcript.user.done",
        state: "transcribing",
        speaker: "user",
        turn_id: event.item_id || event.id || null,
        sequence: event.content_index ?? null,
        text,
        provider_event_type: event.type,
      };
    }

    if (event.type === "conversation.item.done") {
      const item = event.item || {};
      const content = Array.isArray(item.content) ? item.content : [];
      const inputAudio = content.find((part) => part && part.type === "input_audio");
      const text = inputAudio ? textOrNull(inputAudio.transcript) : null;
      if (item.role === "user" && text !== null) {
        return {
          event_type: "transcript.user.done",
          state: "transcribing",
          speaker: "user",
          turn_id: item.id || null,
          sequence: 0,
          text,
          provider_event_type: event.type,
        };
      }
      return null;
    }

    if (event.type === "response.function_call_arguments.done") {
      return {
        event_type: "tool_call.requested",
        state: "tool_calling",
        tool_name: event.name || "",
        provider_call_id: event.call_id || event.item_id || null,
        tool_status: "requested",
        safe_summary: `${event.name || "tool"} requested.`,
        provider_event_type: event.type,
        provider_raw_arguments: event.arguments || "",
      };
    }

    if (event.type === "response.done") {
      return {
        event_type: "response.done",
        state: "speaking",
        provider_event_type: event.type,
      };
    }

    if (event.type === "error") {
      return {
        event_type: "session.error",
        state: "error",
        provider_event_type: "error",
      };
    }

    return null;
  }

  function buildSafeToolOutput(toolResponse) {
    return JSON.stringify({
      safe_summary: toolResponse.safe_summary,
      result: toolResponse.result,
      handoff_required: toolResponse.handoff_required,
      handoff_reason: toolResponse.handoff_reason,
      error_code: toolResponse.error_code,
    });
  }

  function sendOpenAIToolResult(dataChannel, providerCallId, toolResponse) {
    if (!dataChannel || dataChannel.readyState !== "open") {
      return;
    }
    dataChannel.send(
      JSON.stringify({
        type: "conversation.item.create",
        item: {
          type: "function_call_output",
          call_id: providerCallId,
          output: buildSafeToolOutput(toolResponse),
        },
      }),
    );
  }

  function sendOpenAIResponseCreate(dataChannel) {
    if (!dataChannel || dataChannel.readyState !== "open") {
      return;
    }
    dataChannel.send(JSON.stringify({ type: "response.create" }));
  }

  window.voiceAgentsOpenAIRealtimeAdapter = {
    normalizeOpenAIRealtimeEvent,
    sendOpenAIToolResult,
    sendOpenAIResponseCreate,
  };
})();
