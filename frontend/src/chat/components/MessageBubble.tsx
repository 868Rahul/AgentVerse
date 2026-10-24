import React from "react";
import { Collapse, Tag } from "antd";
import { RobotOutlined, ToolOutlined, WarningOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Message, ToolCall } from "../../types";
import { TOOL_LABELS, handoffTarget, isHandoffTool } from "../../agents";

interface MessageBubbleProps {
  message: Message;
  // true only for the message that is currently being generated
  isStreaming: boolean;
}

const TypingDots = () => (
  <span className="typing-dots" aria-label="Generating answer">
    <span />
    <span />
    <span />
  </span>
);

const ToolCalls: React.FC<{ calls: ToolCall[] }> = ({ calls }) => (
  <Collapse
    ghost
    size="small"
    className="tool-calls mb-2"
    items={[
      {
        key: "tools",
        label: (
          <span className="text-xs text-slate-500">
            <ToolOutlined className="mr-1.5" />
            {[...new Set(calls.map((call) => TOOL_LABELS[call.name] ?? call.name))].join(" · ")}
          </span>
        ),
        children: (
          <div className="space-y-3">
            {calls.map((call, index) => (
              <div key={call.id ?? index} className="text-xs">
                <div className="font-medium text-slate-600 mb-1">
                  {call.name}
                  <span className="font-normal text-slate-400"> {JSON.stringify(call.args)}</span>
                </div>
                {call.result && <pre className="tool-result">{call.result}</pre>}
              </div>
            ))}
          </div>
        ),
      },
    ]}
  />
);

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, isStreaming }) => {
  const { type, content, toolCall, isError } = message;

  if (type === "user") {
    return (
      <div className="flex justify-end mb-6">
        <div className="max-w-[85%] bg-indigo-600 text-white px-4 py-2.5 rounded-2xl rounded-br-md whitespace-pre-wrap break-words shadow-sm">
          {content}
        </div>
      </div>
    );
  }

  const calls = toolCall?.calls ?? [];
  const handoffs = calls.filter((call) => call.name.startsWith("transfer_to_"));
  const toolCalls = calls.filter((call) => !isHandoffTool(call.name));
  const waiting = isStreaming && !content;

  return (
    <div className="flex gap-3 mb-6">
      <div
        className={`w-8 h-8 shrink-0 rounded-full flex items-center justify-center ${
          isError ? "bg-red-100 text-red-500" : "bg-indigo-100 text-indigo-600"
        }`}
      >
        {isError ? <WarningOutlined /> : <RobotOutlined />}
      </div>
      <div className="flex-1 min-w-0">
        {handoffs.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1">
            {handoffs.map((call, index) => (
              <Tag key={call.id ?? index} color="purple" bordered={false}>
                Routed to {handoffTarget(call.name)}
              </Tag>
            ))}
          </div>
        )}
        {toolCalls.length > 0 && <ToolCalls calls={toolCalls} />}
        <div
          className={`inline-block max-w-full rounded-2xl rounded-tl-md px-4 py-3 shadow-sm ${
            isError ? "bg-red-50 text-red-700 border border-red-200" : "bg-white border border-slate-200 text-slate-800"
          }`}
        >
          {waiting ? (
            <span className="flex items-center gap-2 text-sm text-slate-400">
              <TypingDots />
              {toolCalls.length > 0 ? "Working on it…" : null}
            </span>
          ) : (
            <div className="markdown">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
