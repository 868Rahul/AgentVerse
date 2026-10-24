import React from "react";
import { Button, Layout } from "antd";
import { PlusOutlined, TeamOutlined } from "@ant-design/icons";
import SessionListItem from "./SessionListItem";
import { ChatSession } from "../types";

interface SidebarProps {
  collapsed: boolean;
  isMobile: boolean;
  onBreakpoint: (broken: boolean) => void;
  onClose: () => void;
  sessions: ChatSession[];
  currentThreadId: string | null;
  directoryActive: boolean;
  onNewChat: () => void;
  onSelectSession: (session: ChatSession) => void;
  onDeleteSession: (threadId: string) => void;
  onOpenDirectory: () => void;
}

const { Sider } = Layout;

const Sidebar: React.FC<SidebarProps> = ({
  collapsed,
  isMobile,
  onBreakpoint,
  onClose,
  sessions,
  currentThreadId,
  directoryActive,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onOpenDirectory,
}) => {
  const recent = [...sessions].sort((a, b) => b.lastUpdated - a.lastUpdated);

  return (
    <>
      {/* On phones the sidebar slides over the page, tapping outside closes it */}
      {isMobile && !collapsed && <div className="fixed inset-0 z-40 bg-slate-900/40" onClick={onClose} aria-hidden="true" />}
      <Sider
        collapsed={collapsed}
        collapsedWidth={0}
        breakpoint="md"
        onBreakpoint={onBreakpoint}
        trigger={null}
        width={264}
        style={{
          background: "#0f172a",
          ...(isMobile ? { position: "fixed", zIndex: 50, height: "100vh", left: 0, top: 0 } : {}),
        }}
      >
        <div className="flex flex-col h-screen">
          <div className="h-16 shrink-0 flex items-center gap-3 px-5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 text-white font-bold text-sm flex items-center justify-center">
              AV
            </div>
            <span className="text-white text-lg font-semibold tracking-tight">AgentVerse</span>
          </div>
          <div className="px-3">
            <Button type="primary" size="large" block icon={<PlusOutlined />} onClick={onNewChat}>
              New chat
            </Button>
          </div>
          <div className="px-5 pt-6 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Recent chats</div>
          <nav className="flex-1 overflow-y-auto px-2 pb-4 space-y-0.5 sider-scroll" aria-label="Recent chats">
            {recent.length === 0 && <p className="px-3 text-sm text-slate-500">No conversations yet</p>}
            {recent.map((session) => (
              <SessionListItem
                key={session.threadId}
                session={session}
                active={!directoryActive && session.threadId === currentThreadId}
                onSelect={onSelectSession}
                onDelete={onDeleteSession}
              />
            ))}
          </nav>
          <div className="shrink-0 border-t border-slate-800 p-2">
            <button
              type="button"
              onClick={onOpenDirectory}
              className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                directoryActive ? "bg-slate-700/80 text-white" : "text-slate-300 hover:bg-slate-800 hover:text-white"
              }`}
            >
              <TeamOutlined />
              Employee directory
            </button>
          </div>
        </div>
      </Sider>
    </>
  );
};

export default Sidebar;
