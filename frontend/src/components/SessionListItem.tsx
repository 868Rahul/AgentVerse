import React from "react";
import { Popconfirm } from "antd";
import { DeleteOutlined } from "@ant-design/icons";
import { ChatSession } from "../types";
import { getAgent } from "../agents";

interface SessionListItemProps {
  session: ChatSession;
  active: boolean;
  onSelect: (session: ChatSession) => void;
  onDelete: (threadId: string) => void;
}

const SessionListItem: React.FC<SessionListItemProps> = ({ session, active, onSelect, onDelete }) => {
  const agent = getAgent(session.agentId);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect(session)}
      onKeyDown={(e) => e.key === "Enter" && onSelect(session)}
      title={`${session.name} · ${agent.name}`}
      className={`group flex items-center gap-2.5 px-3 py-2 rounded-lg cursor-pointer text-sm transition-colors ${
        active ? "bg-slate-700/80 text-white" : "text-slate-300 hover:bg-slate-800 hover:text-white"
      }`}
    >
      <span className="text-slate-500 shrink-0">{agent.icon}</span>
      <span className="flex-1 truncate">{session.name}</span>
      <Popconfirm
        title="Delete this chat?"
        okText="Delete"
        okButtonProps={{ danger: true }}
        onConfirm={(e) => {
          e?.stopPropagation();
          onDelete(session.threadId);
        }}
        onCancel={(e) => e?.stopPropagation()}
      >
        <button
          type="button"
          onClick={(e) => e.stopPropagation()}
          className="shrink-0 text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
          aria-label="Delete chat"
        >
          <DeleteOutlined />
        </button>
      </Popconfirm>
    </div>
  );
};

export default SessionListItem;
