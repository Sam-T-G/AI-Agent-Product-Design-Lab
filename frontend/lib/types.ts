/** TypeScript types matching backend models. */

export interface ToolConfig {
  name: string;
  params: Record<string, any>;
}

export interface Agent {
  id: string;
  name: string;
  role: string;
  system_prompt: string;
  tools: ToolConfig[];
  parameters: Record<string, any>;
  photo_injection_enabled: boolean;
  photo_injection_features: string[];
  parent_id: string | null;
  position_x: number | null;
  position_y: number | null;
  created_at: string;
  updated_at: string;
}

export interface AgentCreate {
  name: string;
  role: string;
  system_prompt: string;
  tools?: ToolConfig[];
  parameters?: Record<string, any>;
  photo_injection_enabled?: boolean;
  photo_injection_features?: string[];
  parent_id?: string | null;
  position_x?: number | null;
  position_y?: number | null;
}

export interface Link {
  id: string;
  parent_agent_id: string;
  child_agent_id: string;
  created_at: string;
}

export interface LinkCreate {
  parent_agent_id: string;
  child_agent_id: string;
}

export interface Run {
  id: string;
  root_agent_id: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  input: Record<string, any>;
  output: Record<string, string>;
  logs: Array<{
    agent_id: string;
    timestamp: string;
    message: string;
    level?: string;
  }>;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  error?: string;
}

export interface RunRequest {
  root_agent_id: string;
  input: Record<string, any>;
  images?: string[]; // Base64-encoded image strings
}

// React Flow types
export interface AgentNode {
  id: string;
  type: "agent";
  position: { x: number; y: number };
  data: {
    agent: Agent;
  };
}

export interface AgentEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
}


