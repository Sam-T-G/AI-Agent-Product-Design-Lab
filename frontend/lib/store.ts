/** Zustand store with Immer for state management. */
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import { Agent, AgentNode, AgentEdge } from "./types";

interface GraphSlice {
	nodes: AgentNode[];
	edges: AgentEdge[];
	selectedNodeId: string | null;
	setNodes: (nodes: AgentNode[]) => void;
	setEdges: (edges: AgentEdge[]) => void;
	addNode: (node: AgentNode) => void;
	removeNode: (nodeId: string) => void;
	updateNode: (nodeId: string, data: Partial<AgentNode>) => void;
	addEdge: (edge: AgentEdge) => void;
	removeEdge: (edgeId: string) => void;
	setSelectedNode: (nodeId: string | null) => void;
}

interface RunSlice {
	currentRunId: string | null;
	setCurrentRun: (runId: string | null) => void;
}

export const useGraphStore = create<GraphSlice>()(
	immer((set) => ({
		nodes: [],
		edges: [],
		selectedNodeId: null,
		setNodes: (nodes) => set({ nodes }),
		setEdges: (edges) => set({ edges }),
		addNode: (node) =>
			set((state) => {
				state.nodes.push(node);
			}),
		removeNode: (nodeId) =>
			set((state) => {
				state.nodes = state.nodes.filter((n) => n.id !== nodeId);
				state.edges = state.edges.filter(
					(e) => e.source !== nodeId && e.target !== nodeId
				);
			}),
		updateNode: (nodeId, data) =>
			set((state) => {
				const node = state.nodes.find((n) => n.id === nodeId);
				if (node) {
					Object.assign(node, data);
				}
			}),
		addEdge: (edge) =>
			set((state) => {
				// Check if edge already exists (by ID or by source-target pair)
				const exists = state.edges.some(
					(e) =>
						e.id === edge.id ||
						(e.source === edge.source && e.target === edge.target)
				);
				if (!exists) {
					state.edges.push(edge);
				}
			}),
		removeEdge: (edgeId) =>
			set((state) => {
				state.edges = state.edges.filter((e) => e.id !== edgeId);
			}),
		setSelectedNode: (nodeId) => set({ selectedNodeId: nodeId }),
	}))
);

export const useRunStore = create<RunSlice>()(
	immer((set) => ({
		currentRunId: null,
		setCurrentRun: (runId) => set({ currentRunId: runId }),
	}))
);
