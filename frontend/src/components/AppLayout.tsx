import React, { useState } from "react";
import { Layout } from "antd";
import { MenuFoldOutlined, MenuUnfoldOutlined } from "@ant-design/icons";
import { Outlet, useMatch, useNavigate } from "react-router-dom";
import AgentSelector from "./AgentSelector";
import Sidebar from "./Sidebar";
import { DEFAULT_AGENT, useAppContext } from "../AppContext";
import { ChatSession } from "../types";

/** Shell around every page: sidebar, header and the routed page (<Outlet />) */
const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const chatMatch = useMatch("/chat/:threadId?");
  const directoryActive = useMatch("/directory") !== null;
  const currentThreadId = chatMatch?.params.threadId ?? null;
  const { agentId, setAgentId, sessions, deleteSession } = useAppContext();
  const [collapsed, setCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  const closeSidebarOnMobile = () => {
    if (isMobile) setCollapsed(true);
  };

  const handleNewChat = () => {
    closeSidebarOnMobile();
    navigate("/chat");
  };

  const handleSelectSession = (session: ChatSession) => {
    closeSidebarOnMobile();
    setAgentId(session.agentId || DEFAULT_AGENT);
    navigate(`/chat/${session.threadId}`);
  };

  const handleDeleteSession = (threadId: string) => {
    deleteSession(threadId);
    if (threadId === currentThreadId) navigate("/chat");
  };

  const handleSelectAgent = (value: string) => {
    setAgentId(value);
    navigate("/chat");
  };

  return (
    <Layout className="h-screen overflow-hidden">
      <Sidebar
        collapsed={collapsed}
        isMobile={isMobile}
        onBreakpoint={(broken) => {
          setIsMobile(broken);
          setCollapsed(broken);
        }}
        onClose={() => setCollapsed(true)}
        sessions={sessions}
        currentThreadId={currentThreadId}
        directoryActive={directoryActive}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
        onOpenDirectory={() => {
          closeSidebarOnMobile();
          navigate("/directory");
        }}
      />
      <Layout className="bg-slate-50">
        <header className="h-16 shrink-0 flex items-center justify-between gap-3 px-4 bg-white border-b border-slate-200">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              onClick={() => setCollapsed(!collapsed)}
              className="w-9 h-9 shrink-0 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800 flex items-center justify-center text-lg"
              aria-label={collapsed ? "Show sidebar" : "Hide sidebar"}
            >
              {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            </button>
            {directoryActive ? (
              <h1 className="text-base font-semibold text-slate-800 truncate">Employee directory</h1>
            ) : (
              <AgentSelector value={agentId} onChange={handleSelectAgent} />
            )}
          </div>
          <span className="hidden lg:inline text-xs text-slate-400 whitespace-nowrap">Gemini · LangGraph · RAG</span>
        </header>
        <main className="flex-1 min-h-0">
          <Outlet />
        </main>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
