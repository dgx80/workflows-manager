/**
 * TypeScript types for CICD Monitor.
 */

export interface Event {
  timestamp: string;
  agent: string;
  action: "start" | "end" | "error" | string;
  workflow: string | null;
  parent: string | null;
  metadata: Record<string, unknown>;
}

export interface MonitorState {
  active_agent: string | null;
  active_workflow: string | null;
  started_at: string | null;
  event_count: number;
}

export interface AgentInfo {
  icon: string;
  label: string;
  color: string;
}

export type AgentName =
  | "architect"
  | "coder"
  | "tester"
  | "analyst"
  | "pm"
  | "cicd"
  | "master"
  | "builder";

export const AGENTS: Record<AgentName, AgentInfo> = {
  architect: { icon: "🏗️", label: "Architect", color: "#f59e0b" },
  coder: { icon: "💻", label: "Coder", color: "#3b82f6" },
  tester: { icon: "🧪", label: "Tester", color: "#10b981" },
  analyst: { icon: "🔍", label: "Analyst", color: "#8b5cf6" },
  pm: { icon: "📋", label: "PM", color: "#ec4899" },
  cicd: { icon: "🔄", label: "CI/CD", color: "#6366f1" },
  master: { icon: "👑", label: "Master", color: "#f43f5e" },
  builder: { icon: "🔨", label: "Builder", color: "#14b8a6" },
};

export interface WebSocketMessage {
  type: "init" | "event" | "error";
  events?: Event[];
  state?: MonitorState;
  event?: Event;
  message?: string;
}
