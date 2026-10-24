import { Dispatch, SetStateAction, useRef, useState } from "react";
import { App } from "antd";
import { API_BASE_URL } from "../../api";
import { Message, ToolCall } from "../../types";

const FALLBACK_ERROR = "Request failed, please try again later.";

/**
 * Sends a message to POST /chat/stream and applies the Server-Sent Events to the message list:
 * token -> append text, message -> tool calls / results / final answer, error -> red bubble, end -> done.
 */
export function useStreamChat(setMessages: Dispatch<SetStateAction<Message[]>>) {
  const { message } = App.useApp();
  const [isStreaming, setIsStreaming] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);

  const updateLastMessage = (update: (msg: Message) => Message) => {
    setMessages((prev) => prev.map((msg, i) => (i === prev.length - 1 ? update(msg) : msg)));
  };

  const handleError = (error: string) => {
    message.error(error || FALLBACK_ERROR);
    // Show the error in the bubble instead of leaving an empty answer
    updateLastMessage((msg) => (msg.content ? msg : { ...msg, content: error || FALLBACK_ERROR, isError: true }));
  };

  const handleMessage = (content: any) => {
    if (content.type === "ai" && content.tool_calls?.length > 0) {
      updateLastMessage((msg) => {
        const known = msg.toolCall?.calls ?? [];
        const added = (content.tool_calls as ToolCall[]).filter((call) => !known.some((c) => c.id && c.id === call.id));
        return { ...msg, toolCall: { calls: [...known, ...added] } };
      });
    } else if (content.type === "ai" && content.content) {
      // the final message replaces the streamed tokens (it is the complete, redacted answer)
      updateLastMessage((msg) => ({ ...msg, content: content.content }));
    }
    if (content.type === "tool") {
      updateLastMessage((msg) => ({
        ...msg,
        toolCall: {
          calls: (msg.toolCall?.calls ?? []).map((call) =>
            call.id === content.tool_call_id ? { ...call, result: content.content } : call
          ),
        },
      }));
    }
  };

  const sendMessage = async (input: string, threadId: string, agentId: string) => {
    if (!input.trim() || isStreaming) return;
    setIsStreaming(true);
    const controller = new AbortController();
    controllerRef.current = controller;

    const now = Date.now();
    setMessages((prev) => [
      ...prev,
      { id: `user_${now}`, type: "user", content: input },
      { id: `ai_${now}`, type: "ai", content: "" },
    ]);

    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ thread_id: threadId, message: input, agent_id: agentId }),
        signal: controller.signal,
      });
      if (!response.ok || !response.body) {
        let detail = `Server responded with ${response.status}`;
        try {
          detail = (await response.json()).detail ?? detail;
        } catch {
          // not JSON
        }
        throw new Error(detail);
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      // A network chunk can end in the middle of an SSE line, keep the rest for the next chunk
      let buffer = "";
      let ended = false;

      while (!ended) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          let data: any;
          try {
            data = JSON.parse(line.slice("data: ".length));
          } catch {
            console.error("Invalid stream event:", line);
            continue;
          }
          switch (data.type) {
            case "token":
              updateLastMessage((msg) => ({ ...msg, content: msg.content + data.content }));
              break;
            case "message":
              handleMessage(data.content);
              break;
            case "error":
              handleError(data.content);
              break;
            case "end":
              ended = true;
              reader.cancel();
              break;
          }
        }
      }
    } catch (error: any) {
      if (error?.name === "AbortError") {
        updateLastMessage((msg) => (msg.content ? msg : { ...msg, content: "_Stopped._" }));
      } else {
        console.error("Request failed:", error);
        handleError(error?.message || FALLBACK_ERROR);
      }
    } finally {
      controllerRef.current = null;
      setIsStreaming(false);
    }
  };

  /** Cancel the answer that is being generated */
  const stop = () => controllerRef.current?.abort();

  return { sendMessage, stop, isStreaming };
}
