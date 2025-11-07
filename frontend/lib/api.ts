/** API client for backend communication. */
// Use relative "/api" so the frontend can proxy to the backend at a single public URL
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "/api";

import {
	Agent,
	AgentCreate,
	Link,
	LinkCreate,
	Run,
	RunRequest,
	Session,
	SessionCreate,
} from "./types";

// Helper to get session_id from localStorage
function getSessionId(): string | null {
	try {
		return typeof window !== "undefined"
			? localStorage.getItem("SESSION_ID")
			: null;
	} catch {
		return null;
	}
}

// Helper to build query string with session_id
function withSession(query: Record<string, string> = {}): string {
	const sessionId = getSessionId();
	const params = new URLSearchParams({
		...query,
		...(sessionId ? { session_id: sessionId } : {}),
	});
	return params.toString();
}

// Sessions
export async function listSessions(): Promise<Session[]> {
	const res = await fetch(`${API_BASE}/sessions`);
	if (!res.ok) throw new Error(`Failed to list sessions: ${res.statusText}`);
	return res.json();
}

export async function createSession(data: SessionCreate): Promise<Session> {
	const res = await fetch(`${API_BASE}/sessions`, {
		method: "POST",
		headers: authHeaders(),
		body: JSON.stringify(data),
	});
	if (!res.ok) throw new Error(`Failed to create session: ${res.statusText}`);
	return res.json();
}

export async function getSession(id: string): Promise<Session> {
	const res = await fetch(`${API_BASE}/sessions/${id}`);
	if (!res.ok) throw new Error(`Failed to get session: ${res.statusText}`);
	return res.json();
}

export async function deleteSession(id: string): Promise<void> {
	const res = await fetch(`${API_BASE}/sessions/${id}`, {
		method: "DELETE",
	});
	if (!res.ok) throw new Error(`Failed to delete session: ${res.statusText}`);
}

function authHeaders() {
	const headers: Record<string, string> = {
		"Content-Type": "application/json",
	};
	try {
		const key =
			typeof window !== "undefined"
				? localStorage.getItem("GEMINI_API_KEY")
				: null;
		if (key) headers["X-Gemini-Api-Key"] = key;
	} catch {}
	return headers;
}

// Agents
export async function listAgents(sessionId?: string): Promise<Agent[]> {
	const sid = sessionId || getSessionId();
	if (!sid) throw new Error("Session ID is required");
	const res = await fetch(`${API_BASE}/agents?${withSession()}`);
	if (!res.ok) throw new Error(`Failed to list agents: ${res.statusText}`);
	return res.json();
}

export async function createAgent(
	data: AgentCreate,
	sessionId?: string
): Promise<Agent> {
	const sid = sessionId || getSessionId();
	if (!sid) throw new Error("Session ID is required");
	const res = await fetch(`${API_BASE}/agents?${withSession()}`, {
		method: "POST",
		headers: authHeaders(),
		body: JSON.stringify(data),
	});
	if (!res.ok) throw new Error(`Failed to create agent: ${res.statusText}`);
	return res.json();
}

export async function getAgent(id: string, sessionId?: string): Promise<Agent> {
	const sid = sessionId || getSessionId();
	if (!sid) throw new Error("Session ID is required");
	const res = await fetch(`${API_BASE}/agents/${id}?${withSession()}`);
	if (!res.ok) throw new Error(`Failed to get agent: ${res.statusText}`);
	return res.json();
}

export async function updateAgent(
	id: string,
	data: Partial<AgentCreate>,
	sessionId?: string
): Promise<Agent> {
	const sid = sessionId || getSessionId();
	if (!sid) throw new Error("Session ID is required");

	try {
		const res = await fetch(`${API_BASE}/agents/${id}?${withSession()}`, {
			method: "PUT",
			headers: authHeaders(),
			body: JSON.stringify(data),
		});

		if (!res.ok) {
			const errorText = await res.text();
			let errorMessage = `Failed to update agent: ${res.statusText}`;
			try {
				const errorJson = JSON.parse(errorText);
				if (errorJson.detail) {
					errorMessage = `Failed to update agent: ${errorJson.detail}`;
				}
			} catch {
				// Use default error message
			}
			throw new Error(errorMessage);
		}

		return res.json();
	} catch (err) {
		if (err instanceof Error) {
			// Re-throw with more context
			if (err.message.includes("fetch") || err.message.includes("network")) {
				throw new Error(
					"Network error: Please check your connection and try again"
				);
			}
			throw err;
		}
		throw new Error("Failed to update agent: Unknown error");
	}
}

export async function deleteAgent(
	id: string,
	sessionId?: string
): Promise<void> {
	const sid = sessionId || getSessionId();
	if (!sid) throw new Error("Session ID is required");
	const res = await fetch(`${API_BASE}/agents/${id}?${withSession()}`, {
		method: "DELETE",
	});
	if (!res.ok) throw new Error(`Failed to delete agent: ${res.statusText}`);
}

// Links
export async function createLink(
	data: LinkCreate,
	sessionId?: string
): Promise<Link> {
	const sid = sessionId || getSessionId();
	if (!sid) throw new Error("Session ID is required");
	const res = await fetch(`${API_BASE}/links?${withSession()}`, {
		method: "POST",
		headers: authHeaders(),
		body: JSON.stringify(data),
	});
	// Treat 409 (conflict/duplicate) as success to keep UX smooth; backend already
	// guarantees idempotency of the relationship via parent_id.
	if (res.status === 409) {
		return {
			id: `conflict-${data.parent_agent_id}-${data.child_agent_id}`,
			parent_agent_id: data.parent_agent_id,
			child_agent_id: data.child_agent_id,
			created_at: new Date().toISOString(),
		} as Link;
	}
	if (!res.ok) throw new Error(`Failed to create link: ${res.statusText}`);
	return res.json();
}

export async function deleteLink(
	data: LinkCreate,
	sessionId?: string
): Promise<void> {
	const sid = sessionId || getSessionId();
	if (!sid) throw new Error("Session ID is required");
	const res = await fetch(`${API_BASE}/links?${withSession()}`, {
		method: "DELETE",
		headers: authHeaders(),
		body: JSON.stringify(data),
	});
	if (!res.ok) throw new Error(`Failed to delete link: ${res.statusText}`);
}

// Runs
export async function createRun(
	data: RunRequest,
	sessionId?: string
): Promise<Run> {
	const sid = sessionId || getSessionId();
	if (!sid) throw new Error("Session ID is required");
	const res = await fetch(`${API_BASE}/runs?${withSession()}`, {
		method: "POST",
		headers: authHeaders(),
		body: JSON.stringify(data),
	});
	if (!res.ok) throw new Error(`Failed to create run: ${res.statusText}`);
	return res.json();
}

export async function getRun(id: string, sessionId?: string): Promise<Run> {
	const sid = sessionId || getSessionId();
	if (!sid) throw new Error("Session ID is required");
	const res = await fetch(`${API_BASE}/runs/${id}?${withSession()}`);
	if (!res.ok) throw new Error(`Failed to get run: ${res.statusText}`);
	return res.json();
}

// SSE helper for streaming runs
export function streamRun(
	runId: string,
	onEvent: (event: { type: string; agent_id?: string; data?: unknown }) => void,
	sessionId?: string
): EventSource {
	const sid = sessionId || getSessionId();
	if (!sid) throw new Error("Session ID is required");

	// EventSource doesn't support custom headers; include API key via query param
	let url = `${API_BASE}/runs/${runId}/stream?${withSession()}`;
	try {
		const key =
			typeof window !== "undefined"
				? localStorage.getItem("GEMINI_API_KEY")
				: null;
		if (key) {
			url = `${url}&api_key=${encodeURIComponent(key)}`;
		}
	} catch {}
	const eventSource = new EventSource(url);

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
