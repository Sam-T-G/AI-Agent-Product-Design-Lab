"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AgentCanvas } from "@/components/canvas/AgentCanvas";
import { AgentDrawer } from "@/components/drawer/AgentDrawer";
import { ChatInterface } from "@/components/chat/ChatInterface";
import { listAgents, createAgent, deleteAgent, createLink, deleteLink, updateAgent } from "@/lib/api";
import { useGraphStore } from "@/lib/store";
import { Agent, AgentNode, AgentEdge, AgentCreate } from "@/lib/types";

export default function LabPage() {
  const queryClient = useQueryClient();
  const { nodes, edges, setNodes, setEdges, selectedNodeId, setSelectedNode } = useGraphStore();
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Create agent mutation with optimistic update
  const createAgentMutation = useMutation({
    mutationFn: (data: AgentCreate) => createAgent(data),
    onMutate: async (newAgent) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ["agents"] });
      // Snapshot previous value
      const previousAgents = queryClient.getQueryData<Agent[]>(["agents"]);
      // Optimistically update
      queryClient.setQueryData<Agent[]>(["agents"], (old = []) => [
        ...old,
        {
          id: `temp-${Date.now()}`,
          ...newAgent,
          position_x: newAgent.position_x ?? null,
          position_y: newAgent.position_y ?? null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        } as Agent,
      ]);
      return { previousAgents };
    },
    onError: (err, newAgent, context) => {
      // Rollback on error
      if (context?.previousAgents) {
        queryClient.setQueryData(["agents"], context.previousAgents);
      }
      console.error("Failed to create agent:", err);
      alert(`Failed to create agent: ${err instanceof Error ? err.message : 'Unknown error'}`);
    },
    onSuccess: () => {
      // Refetch to get real ID and data from DB
      queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
  });

  // Delete agent mutation
  const deleteAgentMutation = useMutation({
    mutationFn: (id: string) => deleteAgent(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      // Close drawer if deleted agent was selected
      if (selectedAgent) {
        setIsDrawerOpen(false);
        setSelectedAgent(null);
        setSelectedNode(null);
      }
    },
    onError: (error) => {
      console.error("Failed to delete agent:", error);
      alert(`Failed to delete agent: ${error instanceof Error ? error.message : 'Unknown error'}`);
    },
  });

  // Create link mutation with optimistic update
  const createLinkMutation = useMutation({
    mutationFn: (data: { parent_agent_id: string; child_agent_id: string }) => createLink(data),
    onMutate: async (linkData) => {
      await queryClient.cancelQueries({ queryKey: ["agents"] });
      const previousAgents = queryClient.getQueryData<Agent[]>(["agents"]);
      // Optimistically update parent_id
      queryClient.setQueryData<Agent[]>(["agents"], (old = []) =>
        old.map((a) =>
          a.id === linkData.child_agent_id
            ? { ...a, parent_id: linkData.parent_agent_id }
            : a
        )
      );
      return { previousAgents };
    },
    onError: (err, linkData, context) => {
      if (context?.previousAgents) {
        queryClient.setQueryData(["agents"], context.previousAgents);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
  });

  // Delete link mutation with optimistic update
  const deleteLinkMutation = useMutation({
    mutationFn: (data: { parent_agent_id: string; child_agent_id: string }) => deleteLink(data),
    onMutate: async (linkData) => {
      await queryClient.cancelQueries({ queryKey: ["agents"] });
      const previousAgents = queryClient.getQueryData<Agent[]>(["agents"]);
      // Optimistically remove parent_id
      queryClient.setQueryData<Agent[]>(["agents"], (old = []) =>
        old.map((a) =>
          a.id === linkData.child_agent_id ? { ...a, parent_id: null } : a
        )
      );
      return { previousAgents };
    },
    onError: (err, linkData, context) => {
      if (context?.previousAgents) {
        queryClient.setQueryData(["agents"], context.previousAgents);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
  });

  // Fetch agents from API
  const { data: agents = [], error: agentsError, isLoading: agentsLoading } = useQuery({
    queryKey: ["agents"],
    queryFn: listAgents,
    retry: 2,
  });

  // Log errors for debugging
  useEffect(() => {
    if (agentsError) {
      console.error("Failed to fetch agents:", agentsError);
    }
  }, [agentsError]);

  // Derive nodes/edges directly from agents (DB is source of truth)
  // This eliminates redundant state storage - agents from React Query are the cache
  const { agentNodes, agentEdges } = useMemo(() => {
    if (agents.length === 0) {
      return { agentNodes: [], agentEdges: [] };
    }

    // Create nodes with positions from DB (always use saved positions)
    const nodes: AgentNode[] = agents.map((agent) => {
      // Always use DB position if available, otherwise calculate fallback
      const position =
        agent.position_x !== null && agent.position_y !== null
          ? { x: agent.position_x, y: agent.position_y }
          : { x: 400, y: 300 }; // Simple fallback for new agents
      
      return {
        id: agent.id,
        type: "agent",
        position,
        data: { agent },
      };
    });

    // Derive edges from parent_id (connections stored in DB)
    const edgeMap = new Map<string, AgentEdge>();
    agents
      .filter((agent) => agent.parent_id)
      .forEach((agent) => {
        const edgeId = `edge-${agent.parent_id}-${agent.id}`;
        edgeMap.set(edgeId, {
          id: edgeId,
          source: agent.parent_id!,
          target: agent.id,
        });
      });

    return { 
      agentNodes: nodes, 
      agentEdges: Array.from(edgeMap.values()) 
    };
  }, [agents]); // Only recalculate when agents change

  // Sync to Zustand store (minimal - only for ReactFlow)
  // Use a ref to track if structure actually changed to avoid unnecessary updates
  const prevAgentsRef = useRef<string>("");
  
  useEffect(() => {
    // Create a simple hash of agent IDs and parent_ids to detect structure changes
    const agentsHash = JSON.stringify(
      agents.map(a => ({ id: a.id, parent_id: a.parent_id, pos_x: a.position_x, pos_y: a.position_y }))
    );
    
    if (agentsHash !== prevAgentsRef.current) {
      setNodes(agentNodes);
      setEdges(agentEdges);
      prevAgentsRef.current = agentsHash;
    }
  }, [agents, agentNodes, agentEdges, setNodes, setEdges]);

  // Handle node click
  const handleNodeClick = (nodeId: string) => {
    const agent = agents.find((a) => a.id === nodeId);
    if (agent) {
      setSelectedAgent(agent);
      setIsDrawerOpen(true);
    }
  };

  // Handle add agent
  const handleAddAgent = () => {
    // Find the highest agent number to avoid duplicates
    const agentNumbers = agents
      .map((a) => {
        const match = a.name.match(/^Agent (\d+)$/);
        return match ? parseInt(match[1], 10) : 0;
      })
      .filter((n) => n > 0);
    const nextNumber = agentNumbers.length > 0 ? Math.max(...agentNumbers) + 1 : agents.length + 1;

    const newAgent: AgentCreate = {
      name: `Agent ${nextNumber}`,
      role: "worker",
      system_prompt: "You are a helpful agent.",
      parameters: {
        temperature: 0.7,
        max_tokens: 1000,
        model: "gemini-1.5-pro",
      },
    };

    createAgentMutation.mutate(newAgent);
  };

  // Handle delete agent
  const handleDeleteAgent = () => {
    if (!selectedNodeId && agents.length === 0) {
      return; // Nothing to delete
    }

    const agentToDelete = selectedNodeId 
      ? agents.find((a) => a.id === selectedNodeId)
      : agents[agents.length - 1];

    if (!agentToDelete) return;

    // Check if agent has children
    const hasChildren = agents.some((a) => a.parent_id === agentToDelete.id);
    const warning = hasChildren 
      ? `Warning: This agent has children. Deleting it will also remove all child agents and connections. Are you sure?`
      : `Are you sure you want to delete "${agentToDelete.name}"? This will remove all connections.`;

    if (confirm(warning)) {
      deleteAgentMutation.mutate(agentToDelete.id);
    }
  };

  // Handle drawer close
  const handleDrawerClose = () => {
    setIsDrawerOpen(false);
    setSelectedAgent(null);
    setSelectedNode(null);
  };

  // Handle drawer save
  const handleDrawerSave = (updatedAgent: Agent) => {
    queryClient.invalidateQueries({ queryKey: ["agents"] });
    setSelectedAgent(updatedAgent);
  };

  // Find root agent (agent with no parent)
  const rootAgent = useMemo(() => {
    return agents.find((agent) => !agent.parent_id);
  }, [agents]);

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 sm:px-6 py-4 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900">
              AI Agent Product Design Lab
            </h1>
            <p className="text-xs sm:text-sm text-gray-600 mt-1">
              Create, connect, and execute modular AI agents
            </p>
          </div>
          {rootAgent && (
            <div className="text-xs sm:text-sm text-gray-600">
              <span className="font-medium">Root:</span> {rootAgent.name}
            </div>
          )}
        </div>
      </header>

      {/* Main Content - Two Column Layout */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* Left Column - Agent Canvas */}
        <div className="flex-1 relative border-b lg:border-b-0 lg:border-r border-gray-200 bg-white min-h-[400px] lg:min-h-0">
                  <AgentCanvas
                    onNodeClick={handleNodeClick}
                    onAddAgent={handleAddAgent}
                    onDeleteAgent={handleDeleteAgent}
                    onConnect={(sourceId, targetId) => {
                      createLinkMutation.mutate({
                        parent_agent_id: sourceId,
                        child_agent_id: targetId,
                      });
                    }}
                    onDisconnect={(sourceId, targetId) => {
                      deleteLinkMutation.mutate({
                        parent_agent_id: sourceId,
                        child_agent_id: targetId,
                      });
                    }}
                    onNodePositionChange={(nodeId, position) => {
                      // Update agent position in backend with optimistic update
                      const agent = agents.find((a) => a.id === nodeId);
                      if (agent) {
                        // Optimistic update - update cache immediately
                        queryClient.setQueryData<Agent[]>(["agents"], (old) => {
                          if (!old) return old;
                          return old.map((a) =>
                            a.id === nodeId
                              ? { ...a, position_x: position.x, position_y: position.y }
                              : a
                          );
                        });

                        // Persist to DB (fire and forget - cache is already updated)
                        updateAgent(nodeId, {
                          position_x: position.x,
                          position_y: position.y,
                        }).catch((err) => {
                          console.error("Failed to update agent position:", err);
                          // On error, refetch to sync with DB
                          queryClient.invalidateQueries({ queryKey: ["agents"] });
                        });
                      }
                    }}
                    selectedNodeId={selectedNodeId}
                  />
        </div>

        {/* Right Column - Chat Interface or Drawer */}
        <div className="w-full lg:w-[500px] xl:w-[600px] flex-shrink-0 lg:border-l border-gray-200 bg-white flex flex-col">
          {isDrawerOpen && selectedAgent ? (
            <AgentDrawer
              agent={selectedAgent}
              onClose={handleDrawerClose}
              onSave={handleDrawerSave}
              onDelete={(agentId) => {
                deleteAgentMutation.mutate(agentId);
              }}
              agents={agents}
            />
          ) : (
            <ChatInterface 
              agentId={selectedNodeId || undefined}
              rootAgentId={rootAgent?.id}
            />
          )}
        </div>
      </div>
    </div>
  );
}
