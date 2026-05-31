import { fetchJson } from "./client";

export interface SkillSummary {
  name: string;
  description: string;
}

export interface ToolCallRecord {
  name: string;
  input: Record<string, unknown>;
}

export interface ChatTurn {
  role: string;
  content: string;
  tool_uses: ToolCallRecord[];
  input_tokens: number;
  output_tokens: number;
  latency_s: number;
  skill_invoked: string | null;
}

export interface ChatResponse {
  session_id: string;
  turn: ChatTurn;
  history_length: number;
}

export const chatApi = {
  health: () =>
    fetchJson<{
      service: string;
      skill_count: number;
      session_count: number;
      anthropic_key_set: boolean;
      model: string;
      max_turns: number;
    }>("/api/chat/health"),
  skills: () => fetchJson<{ count: number; skills: SkillSummary[] }>("/api/chat/skills"),
  send: (message: string, session_id: string | null) =>
    fetchJson<ChatResponse>("/api/chat/chat", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message, session_id }),
    }),
  clear: (session_id: string) =>
    fetchJson<{ session_id: string; cleared: boolean }>(`/api/chat/chat/${session_id}`, {
      method: "DELETE",
    }),
};
