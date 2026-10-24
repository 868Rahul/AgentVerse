import React, { createContext, useContext, useState } from "react";
import { ChatSession, Message } from "./types";

const SESSIONS_KEY = "chatSessions";
export const DEFAULT_AGENT = "oa-assistant";

// localStorage can be unavailable (private mode, blocked storage), the app must still work
function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // ignore, history just won't persist
  }
}

export const loadMessages = (threadId: string) => readJson<Message[]>("chatMessages-" + threadId, []);
export const saveMessages = (threadId: string, messages: Message[]) => writeJson("chatMessages-" + threadId, messages);

interface AppContextType {
  agentId: string;
  setAgentId: (agentId: string) => void;
  sessions: ChatSession[];
  addSession: (session: ChatSession) => void;
  touchSession: (threadId: string) => void;
  deleteSession: (threadId: string) => void;
}

const AppContext = createContext<AppContextType | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [agentId, setAgentId] = useState(DEFAULT_AGENT);
  const [sessions, setSessions] = useState<ChatSession[]>(() => readJson(SESSIONS_KEY, []));

  const updateSessions = (update: (prev: ChatSession[]) => ChatSession[]) => {
    setSessions((prev) => {
      const next = update(prev);
      writeJson(SESSIONS_KEY, next);
      return next;
    });
  };

  const value: AppContextType = {
    agentId,
    setAgentId,
    sessions,
    addSession: (session) => updateSessions((prev) => [...prev, session]),
    touchSession: (threadId) =>
      updateSessions((prev) => prev.map((s) => (s.threadId === threadId ? { ...s, lastUpdated: Date.now() } : s))),
    deleteSession: (threadId) => {
      updateSessions((prev) => prev.filter((s) => s.threadId !== threadId));
      try {
        localStorage.removeItem("chatMessages-" + threadId);
      } catch {
        // ignore
      }
    },
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useAppContext must be used within AppProvider");
  }
  return context;
}
