import React from "react";
import { Button, Input, Tooltip } from "antd";
import { ArrowUpOutlined, StopOutlined } from "@ant-design/icons";

interface MessageInputProps {
  input: string;
  setInput: (value: string) => void;
  onSend: () => void;
  onStop: () => void;
  isStreaming: boolean;
  placeholder?: string;
}

const MessageInput: React.FC<MessageInputProps> = ({ input, setInput, onSend, onStop, isStreaming, placeholder }) => {
  return (
    <div className="shrink-0 border-t border-slate-200 bg-white px-4 pt-3 pb-4">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end gap-2 rounded-2xl border border-slate-300 bg-white px-2 py-2 shadow-sm transition focus-within:border-indigo-400 focus-within:ring-4 focus-within:ring-indigo-50">
          <Input.TextArea
            value={input}
            variant="borderless"
            onChange={(e) => setInput(e.target.value)}
            placeholder={placeholder ?? "Send a message…"}
            autoSize={{ minRows: 1, maxRows: 6 }}
            aria-label="Message"
            // Enter sends, Shift+Enter adds a new line
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                onSend();
              }
            }}
            className="flex-1 !text-[15px]"
          />
          {isStreaming ? (
            <Tooltip title="Stop generating">
              <Button shape="circle" size="large" icon={<StopOutlined />} onClick={onStop} aria-label="Stop generating" />
            </Tooltip>
          ) : (
            <Button
              type="primary"
              shape="circle"
              size="large"
              icon={<ArrowUpOutlined />}
              onClick={onSend}
              disabled={!input.trim()}
              aria-label="Send message"
            />
          )}
        </div>
        <p className="mt-2 text-center text-xs text-slate-400">
          Enter to send · Shift+Enter for a new line · AI answers can be wrong, check important information.
        </p>
      </div>
    </div>
  );
};

export default MessageInput;
