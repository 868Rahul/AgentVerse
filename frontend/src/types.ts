export interface ToolCall {
  id?: string;
  name: string;
  args: Record<string, unknown>;
  result?: string;
}

// Chat message as shown in the UI
export interface Message {
  id: string;
  type: "user" | "ai" | "tool";
  content: string;
  toolCall?: { calls: ToolCall[] };
  isError?: boolean;
}

export interface ChatSession {
  threadId: string;
  name: string;
  lastUpdated: number;
  agentId?: string;
}
