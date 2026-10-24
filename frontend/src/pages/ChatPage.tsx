import React, { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { v4 as uuidv4 } from "uuid";
import { AgentMeta, getAgent } from "../agents";
import { loadMessages, saveMessages, useAppContext } from "../AppContext";
import MessageBubble from "../chat/components/MessageBubble";
import MessageInput from "../chat/components/MessageInput";
import { useStreamChat } from "../chat/hooks/useStreamChat";
import { Message } from "../types";

const Welcome: React.FC<{ agent: AgentMeta; onPick: (question: string) => void }> = ({ agent, onPick }) => (
  <div className="flex flex-col items-center text-center pt-10 sm:pt-20 pb-8">
    <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-500 text-white text-2xl flex items-center justify-center shadow-lg shadow-indigo-200">
      {agent.icon}
    </div>
    <h1 className="mt-5 text-2xl font-semibold text-slate-800">{agent.name}</h1>
    <p className="mt-2 text-slate-500 max-w-lg leading-relaxed">{agent.description}</p>
    <div className="mt-10 grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
      {agent.suggestions.map((question) => (
        <button
          key={question}
          type="button"
          onClick={() => onPick(question)}
          className="text-left px-4 py-3.5 rounded-xl border border-slate-200 bg-white text-sm text-slate-700 hover:border-indigo-300 hover:bg-indigo-50/40 hover:shadow-sm transition"
        >
          {question}
        </button>
      ))}
    </div>
  </div>
);

/** /chat (new conversation) and /chat/:threadId (existing conversation) */
const ChatPage: React.FC = () => {
  const { threadId } = useParams();
  const navigate = useNavigate();
  const { agentId, setAgentId, sessions, addSession, touchSession } = useAppContext();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  // The thread this page just created: its messages are already in state, don't reload them from storage
  const createdThreadRef = useRef<string | null>(null);
  const { sendMessage, stop, isStreaming } = useStreamChat(setMessages);
  const agent = getAgent(agentId);

  // Switching or opening another conversation: stop the running answer and load that conversation
  useEffect(() => {
    if (threadId && threadId === createdThreadRef.current) return;
    stop();
    createdThreadRef.current = null;
    setMessages(threadId ? loadMessages(threadId) : []);
    setInput("");
  }, [threadId]);

  // Reopening a chat (or reloading /chat/<id>) restores the agent it was started with
  useEffect(() => {
    const session = sessions.find((s) => s.threadId === threadId);
    if (session?.agentId && session.agentId !== agentId) {
      setAgentId(session.agentId);
    }
  }, [threadId, sessions]);

  useEffect(() => {
    if (threadId && messages.length > 0) {
      saveMessages(threadId, messages);
    }
  }, [messages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const handleSend = async (text: string = input) => {
    // Enter key also calls this, so an empty input must not start a request
    if (!text.trim() || isStreaming) return;
    setInput("");

    let currentThread = threadId;
    if (!currentThread) {
      // One id for the URL, the sidebar session and the backend conversation memory
      currentThread = uuidv4();
      createdThreadRef.current = currentThread;
      addSession({ threadId: currentThread, name: text.trim().slice(0, 60), lastUpdated: Date.now(), agentId });
      navigate(`/chat/${currentThread}`);
    } else {
      touchSession(currentThread);
    }
    await sendMessage(text, currentThread, agentId);
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6">
          {messages.length === 0 ? (
            <Welcome agent={agent} onPick={handleSend} />
          ) : (
            messages.map((msg, index) => (
              <MessageBubble key={msg.id} message={msg} isStreaming={isStreaming && index === messages.length - 1} />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>
      <MessageInput
        input={input}
        setInput={setInput}
        onSend={() => handleSend()}
        onStop={stop}
        isStreaming={isStreaming}
        placeholder={`Message ${agent.name}…`}
      />
    </div>
  );
};

export default ChatPage;
