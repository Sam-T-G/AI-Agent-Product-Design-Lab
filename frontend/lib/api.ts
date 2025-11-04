/** API client for backend communication. */
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

import { Agent, AgentCreate, Link, LinkCreate, Run, RunRequest } from "./types";

// Agents
export async function listAgents(): Promise<Agent[]> {
  const res = await fetch(`${API_BASE}/agents`);
  if (!res.ok) throw new Error(`Failed to list agents: ${res.statusText}`);
  return res.json();
}

export async function createAgent(data: AgentCreate): Promise<Agent> {
  const res = await fetch(`${API_BASE}/agents`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to create agent: ${res.statusText}`);
  return res.json();
}

export async function getAgent(id: string): Promise<Agent> {
  const res = await fetch(`${API_BASE}/agents/${id}`);
  if (!res.ok) throw new Error(`Failed to get agent: ${res.statusText}`);
  return res.json();
}

export async function updateAgent(id: string, data: Partial<AgentCreate>): Promise<Agent> {
  const res = await fetch(`${API_BASE}/agents/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to update agent: ${res.statusText}`);
  return res.json();
}

export async function deleteAgent(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/agents/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Failed to delete agent: ${res.statusText}`);
}

// Links
export async function createLink(data: LinkCreate): Promise<Link> {
  const res = await fetch(`${API_BASE}/links`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to create link: ${res.statusText}`);
  return res.json();
}

export async function deleteLink(data: LinkCreate): Promise<void> {
  const res = await fetch(`${API_BASE}/links`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to delete link: ${res.statusText}`);
}

// Runs
export async function createRun(data: RunRequest): Promise<Run> {
  const res = await fetch(`${API_BASE}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to create run: ${res.statusText}`);
  return res.json();
}

export async function getRun(id: string): Promise<Run> {
  const res = await fetch(`${API_BASE}/runs/${id}`);
  if (!res.ok) throw new Error(`Failed to get run: ${res.statusText}`);
  return res.json();
}

// SSE helper for streaming runs
export function streamRun(runId: string, onEvent: (event: any) => void): EventSource {
  const eventSource = new EventSource(`${API_BASE}/runs/${runId}/stream`);
  
  eventSource.addEventListener("connected", (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data);
      onEvent({ type: "connected", data: data });
    } catch (err) {
      console.warn("Failed to parse connected event", err);
    }
  });
  
  eventSource.addEventListener("log", (e: MessageEvent) => {
    try {
      onEvent(JSON.parse(e.data));
    } catch (err) {
      console.warn("Failed to parse log event", err);
    }
  });
  
  eventSource.addEventListener("output", (e: MessageEvent) => {
    try {
      onEvent(JSON.parse(e.data));
    } catch (err) {
      console.warn("Failed to parse output event", err);
    }
  });
  
  eventSource.addEventListener("output_chunk", (e: MessageEvent) => {
    try {
      onEvent(JSON.parse(e.data));
    } catch (err) {
      console.warn("Failed to parse output_chunk event", err);
    }
  });
  
  eventSource.addEventListener("status", (e: MessageEvent) => {
    try {
      const event = JSON.parse(e.data);
      onEvent(event);
      if (event.data === "completed") {
        eventSource.close();
      }
    } catch (err) {
      console.warn("Failed to parse status event", err);
    }
  });
  
  eventSource.addEventListener("error", (e: MessageEvent) => {
    try {
      onEvent(JSON.parse(e.data));
      eventSource.close();
    } catch (err) {
      console.warn("Failed to parse error event", err);
    }
  });
  
  eventSource.addEventListener("completed", (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data);
      onEvent({ type: "completed", data: data });
      eventSource.close();
    } catch (err) {
      console.warn("Failed to parse completed event", err);
      eventSource.close();
    }
  });
  
  // Handle open event
  eventSource.onopen = () => {
    console.log("SSE connection opened for run:", runId);
  };
  
  return eventSource;
}

