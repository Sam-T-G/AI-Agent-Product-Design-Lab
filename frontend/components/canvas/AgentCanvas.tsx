"use client";

import React, { useCallback, useMemo, useRef, useEffect } from "react";
import ReactFlow, {
  Node,
  Edge,
  Connection,
  addEdge as rfAddEdge,
  useNodesState,
  useEdgesState,
  Background,
  Controls,
  MiniMap,
  NodeTypes,
  Handle,
  Position,
  NodeChange,
  EdgeChange,
} from "reactflow";
import "reactflow/dist/style.css";

import { AgentNode, AgentEdge } from "@/lib/types";
import { useGraphStore } from "@/lib/store";

// Custom Agent Node Component
function AgentNodeComponent({ data }: { data: { agent: { name: string; role: string } } }) {
  return (
    <div className="bg-white border-2 border-gray-300 rounded-lg shadow-lg p-4 min-w-[200px]">
      <Handle type="target" position={Position.Top} className="w-3 h-3" />
      <div className="text-center">
        <div className="font-semibold text-gray-800">{data.agent.name}</div>
        <div className="text-xs text-gray-700 mt-1">{data.agent.role}</div>
      </div>
      <Handle type="source" position={Position.Bottom} className="w-3 h-3" />
    </div>
  );
}

// Define nodeTypes outside component to avoid React Flow warning
const nodeTypes: NodeTypes = {
  agent: AgentNodeComponent,
};

interface AgentCanvasProps {
  onNodeClick?: (nodeId: string) => void;
  onAddAgent?: () => void;
  onDeleteAgent?: () => void;
  onConnect?: (sourceId: string, targetId: string) => void;
  onDisconnect?: (sourceId: string, targetId: string) => void;
  onNodePositionChange?: (nodeId: string, position: { x: number; y: number }) => void;
  selectedNodeId?: string | null;
}

export function AgentCanvas({ onNodeClick, onAddAgent, onDeleteAgent, onConnect, onDisconnect, onNodePositionChange, selectedNodeId }: AgentCanvasProps) {
  const { nodes, edges, setNodes, setEdges, addNode, addEdge, removeNode, removeEdge, setSelectedNode } = useGraphStore();
  
  // Track last saved positions and debounce timers to minimize DB writes
  const lastSavedPositionsRef = useRef<Map<string, { x: number; y: number }>>(new Map());
  const positionUpdateTimersRef = useRef<Map<string, NodeJS.Timeout>>(new Map());
  const hasInitializedPositionsRef = useRef(false);
  
  // Initialize saved positions from loaded nodes to prevent unnecessary saves
  useEffect(() => {
    if (!hasInitializedPositionsRef.current && nodes.length > 0) {
      nodes.forEach((node) => {
        lastSavedPositionsRef.current.set(node.id, node.position);
      });
      hasInitializedPositionsRef.current = true;
    }
  }, [nodes]);

  // Convert store nodes/edges to ReactFlow format
  const rfNodes: Node[] = useMemo(
    () =>
      nodes.map((n) => ({
        id: n.id,
        type: "agent",
        position: n.position,
        data: n.data,
      })),
    [nodes]
  );

  const rfEdges: Edge[] = useMemo(() => {
    // Deduplicate edges by ID to prevent React key conflicts
    const edgeMap = new Map<string, Edge>();
    edges.forEach((e) => {
      if (!edgeMap.has(e.id)) {
        edgeMap.set(e.id, {
          id: e.id,
          source: e.source,
          target: e.target,
          type: e.type,
        });
      }
    });
    return Array.from(edgeMap.values());
  }, [edges]);

  const [rfNodesState, setRfNodesState, onNodesChange] = useNodesState(rfNodes);
  const [rfEdgesState, setRfEdgesState, onEdgesChange] = useEdgesState(rfEdges);
  
  // Use refs to prevent infinite loops
  const isSyncingRef = useRef(false);
  const prevNodesRef = useRef<string>(JSON.stringify(rfNodes.map(n => ({ id: n.id, type: n.type }))));
  const prevEdgesRef = useRef<string>(JSON.stringify(rfEdges.map(e => ({ id: e.id, source: e.source, target: e.target }))));

  // Sync ReactFlow state with Zustand store (only when structure changes)
  useEffect(() => {
    if (isSyncingRef.current) return;
    
    const currentStructure = JSON.stringify(rfNodes.map(n => ({ id: n.id, type: n.type })));
    const prevStructure = prevNodesRef.current;
    
    if (currentStructure !== prevStructure) {
      isSyncingRef.current = true;
      setRfNodesState(rfNodes);
      prevNodesRef.current = currentStructure;
      // Reset flag after a microtask
      Promise.resolve().then(() => {
        isSyncingRef.current = false;
      });
    }
  }, [rfNodes, setRfNodesState]);

  useEffect(() => {
    if (isSyncingRef.current) return;
    
    const currentStructure = JSON.stringify(rfEdges.map(e => ({ id: e.id, source: e.source, target: e.target })));
    const prevStructure = prevEdgesRef.current;
    
    if (currentStructure !== prevStructure) {
      isSyncingRef.current = true;
      setRfEdgesState(rfEdges);
      prevEdgesRef.current = currentStructure;
      Promise.resolve().then(() => {
        isSyncingRef.current = false;
      });
    }
  }, [rfEdges, setRfEdgesState]);

  // Handle node changes (position updates)
  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      // Update React Flow state immediately for smooth UI
      onNodesChange(changes);
      
      // Debounce position saves to reduce DB writes
      changes.forEach((change) => {
        if (change.type === "position" && change.position) {
          const nodeId = change.id;
          const currentPos = change.position;
          
          // Clear existing timer for this node
          const existingTimer = positionUpdateTimersRef.current.get(nodeId);
          if (existingTimer) {
            clearTimeout(existingTimer);
          }
          
          // Only save if dragging ended or after debounce delay
          if (!change.dragging) {
            const lastSaved = lastSavedPositionsRef.current.get(nodeId);
            
            // Skip if position hasn't changed
            if (lastSaved && lastSaved.x === currentPos.x && lastSaved.y === currentPos.y) {
              return;
            }
            
            // Debounce: wait 300ms after drag ends before saving
            const timer = setTimeout(() => {
              onNodePositionChange?.(nodeId, currentPos);
              lastSavedPositionsRef.current.set(nodeId, { x: currentPos.x, y: currentPos.y });
              positionUpdateTimersRef.current.delete(nodeId);
            }, 300);
            
            positionUpdateTimersRef.current.set(nodeId, timer);
          }
        }
      });
    },
    [onNodesChange, onNodePositionChange]
  );
  
  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      positionUpdateTimersRef.current.forEach((timer) => clearTimeout(timer));
      positionUpdateTimersRef.current.clear();
    };
  }, []);

  // Handle edge changes
  const handleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      // Just pass through to React Flow
      onEdgesChange(changes);
    },
    [onEdgesChange]
  );

  // Handle node clicks
  const onNodeClickInternal = useCallback(
    (_: React.MouseEvent, node: Node) => {
      setSelectedNode(node.id);
      onNodeClick?.(node.id);
    },
    [onNodeClick, setSelectedNode]
  );

  // Handle edge connections
  const onConnectInternal = useCallback(
    (params: Connection) => {
      if (params.source && params.target) {
        const edgeId = `edge-${params.source}-${params.target}`;
        
        // Check if edge already exists to prevent duplicates
        const edgeExists = edges.some(
          (e) =>
            e.id === edgeId ||
            (e.source === params.source && e.target === params.target)
        );
        
        if (!edgeExists) {
          // Update Zustand store first
          const newEdge: AgentEdge = {
            id: edgeId,
            source: params.source,
            target: params.target,
          };
          addEdge(newEdge);
          
          // Update ReactFlow edges with explicit ID
          setRfEdgesState((eds) => {
            const edge: Edge = {
              id: edgeId,
              source: params.source!,
              target: params.target!,
            };
            // Check if edge already exists in ReactFlow state
            if (!eds.some((e) => e.id === edgeId || (e.source === edge.source && e.target === edge.target))) {
              return [...eds, edge];
            }
            return eds;
          });

          // Sync with backend to create parent-child relationship
          if (onConnect) {
            onConnect(params.source, params.target);
          }
        }
      }
    },
    [addEdge, setRfEdgesState, onConnect, edges]
  );

  // Handle node deletion
  const onNodesDelete = useCallback(
    (deleted: Node[]) => {
      deleted.forEach((node) => {
        removeNode(node.id);
      });
    },
    [removeNode]
  );

  // Handle edge deletion
  const onEdgesDelete = useCallback(
    (deleted: Edge[]) => {
      deleted.forEach((edge) => {
        removeEdge(edge.id);
        // Sync with backend to remove parent-child relationship
        if (onDisconnect && edge.source && edge.target) {
          onDisconnect(edge.source, edge.target);
        }
      });
    },
    [removeEdge, onDisconnect]
  );

  return (
    <div className="w-full h-full relative">
      <ReactFlow
        nodes={rfNodesState}
        edges={rfEdgesState}
                onNodesChange={handleNodesChange}
                onEdgesChange={handleEdgesChange}
                onConnect={onConnectInternal}
                onNodeClick={onNodeClickInternal}
        onNodesDelete={onNodesDelete}
        onEdgesDelete={onEdgesDelete}
        nodeTypes={nodeTypes}
        fitView
        className="bg-gray-50"
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
      
      {/* Action Buttons */}
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        <button
          onClick={onAddAgent}
          className="bg-blue-600 hover:bg-blue-700 text-white rounded-full w-12 h-12 shadow-lg flex items-center justify-center text-2xl font-bold transition-colors"
          title="Add Agent"
        >
          +
        </button>
        <button
          onClick={onDeleteAgent}
          disabled={!selectedNodeId}
          className="bg-red-600 hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-full w-12 h-12 shadow-lg flex items-center justify-center text-xl font-bold transition-colors"
          title="Delete Selected Agent"
        >
          ×
        </button>
      </div>
    </div>
  );
}

