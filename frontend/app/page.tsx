"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AgentCanvas } from "@/components/canvas/AgentCanvas";
import { AgentDrawer } from "@/components/drawer/AgentDrawer";
import { ChatInterface } from "@/components/chat/ChatInterface";
import { ApiKeyModal } from "@/components/modal/ApiKeyModal";
import { SessionSelector } from "@/components/modal/SessionSelector";
import { listAgents, createAgent, deleteAgent, createLink, deleteLink, updateAgent, getSession } from "@/lib/api";
import { useGraphStore } from "@/lib/store";
import { Agent, AgentNode, AgentEdge, AgentCreate, Session } from "@/lib/types";

export default function LabPage() {
  const queryClient = useQueryClient();
  const { setNodes, setEdges, selectedNodeId, setSelectedNode } = useGraphStore();
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [showSessionSelector, setShowSessionSelector] = useState(false);
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [hasApiKey, setHasApiKey] = useState(false);
  const [hasSession, setHasSession] = useState(false);
  const [currentSession, setCurrentSession] = useState<Session | null>(null);

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

  // Fetch agents from API (only when session is available)
  const { data: agents = [], error: agentsError } = useQuery({
    queryKey: ["agents"],
    queryFn: listAgents,
    retry: 2,
    enabled: hasSession, // Only fetch when session is selected
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
    // Hash includes display-impacting fields so updates reflect immediately
    const agentsHash = JSON.stringify(
      agents.map(a => ({ id: a.id, parent_id: a.parent_id, pos_x: a.position_x, pos_y: a.position_y, name: a.name, role: a.role, updated_at: a.updated_at }))
    );
    
    if (agentsHash !== prevAgentsRef.current) {
      setNodes(agentNodes);
      setEdges(agentEdges);
      prevAgentsRef.current = agentsHash;
    }
  }, [agents, agentNodes, agentEdges, setNodes, setEdges]);

  // Load current session info
  useEffect(() => {
    const loadSessionInfo = async () => {
      if (typeof window !== "undefined") {
        try {
          const sessionId = localStorage.getItem("SESSION_ID");
          if (sessionId) {
            try {
              const session = await getSession(sessionId);
              setCurrentSession(session);
            } catch {
              // Session might not exist, clear it
              localStorage.removeItem("SESSION_ID");
              setCurrentSession(null);
            }
          }
        } catch {}
      }
    };
    if (hasSession) {
      loadSessionInfo();
    }
  }, [hasSession]);

  // Check for session and API key on mount
  // Always require session first, then API key
  useEffect(() => {
    if (typeof window !== "undefined") {
      const checkSession = () => {
        try {
          const sessionId = localStorage.getItem("SESSION_ID");
          if (sessionId && sessionId.trim().length > 0) {
            setHasSession(true);
            setShowSessionSelector(false);
            checkApiKey();
          } else {
            setHasSession(false);
            setShowSessionSelector(true);
          }
        } catch {
          setHasSession(false);
          setShowSessionSelector(true);
        }
      };
      
      const checkApiKey = () => {
        try {
          const apiKey = localStorage.getItem("GEMINI_API_KEY");
          if (apiKey && apiKey.trim().length > 0) {
            setHasApiKey(true);
            setShowApiKeyModal(false);
          } else {
            setHasApiKey(false);
            setShowApiKeyModal(true);
          }
        } catch {
          setHasApiKey(false);
          setShowApiKeyModal(true);
        }
      };
      
      // Always start with session check
      checkSession();
    }
  }, []);

  // Handle manual session switch
  const handleSwitchSession = () => {
    setShowSessionSelector(true);
    // Don't clear session immediately - let user select new one
    // The selector will update it when a new session is chosen
  };

  // Handle session selection
  const handleSessionSelect = async (sessionId: string | null) => {
    if (!sessionId) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("SESSION_ID");
      }
      setHasSession(false);
      setCurrentSession(null);
      setShowSessionSelector(true);
      queryClient.removeQueries({ queryKey: ["agents"] });
      return;
    }

    if (typeof window !== "undefined") {
      localStorage.setItem("SESSION_ID", sessionId);
    }
    setHasSession(true);
    setShowSessionSelector(false);
    
    // Load session info
    try {
      const session = await getSession(sessionId);
      setCurrentSession(session);
    } catch {
      setCurrentSession(null);
    }
    
    // After session is selected, check for API key
    if (typeof window !== "undefined") {
      try {
        const apiKey = localStorage.getItem("GEMINI_API_KEY");
        if (apiKey && apiKey.trim().length > 0) {
          setHasApiKey(true);
          setShowApiKeyModal(false);
        } else {
          setHasApiKey(false);
          setShowApiKeyModal(true);
        }
      } catch {
        setHasApiKey(false);
        setShowApiKeyModal(true);
      }
    }
    
    // Invalidate queries to reload data for new session
    queryClient.invalidateQueries({ queryKey: ["agents"] });
  };

  // Handle API key save
  const handleApiKeySave = (apiKey: string) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("GEMINI_API_KEY", apiKey);
    }
    setHasApiKey(true);
    setShowApiKeyModal(false);
  };

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
        model: "gemini-2.5-flash",
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
      {/* Session Selector Modal - Required first */}
      <SessionSelector
        isOpen={showSessionSelector}
        onSelect={handleSessionSelect}
      />

      {/* API Key Modal - Required after session selection */}
      <ApiKeyModal
        isOpen={showApiKeyModal && hasSession}
        onSave={handleApiKeySave}
      />

      {/* Block UI if no session or no API key */}
      {(!hasSession || !hasApiKey) && (
        <div className="absolute inset-0 z-[100] bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <p className="text-gray-600">
              {!hasSession ? "Please select or create a session to continue" : "Please enter your API key to continue"}
            </p>
          </div>
        </div>
      )}

      {/* Main Content - Only show if session and API key are set */}
      {hasSession && hasApiKey && (
        <>
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
          <div className="flex items-center gap-3">
            {currentSession && (
              <div className="text-xs sm:text-sm text-gray-600">
                <span className="font-medium">Session:</span> {currentSession.name}
              </div>
            )}
            {rootAgent && (
              <div className="text-xs sm:text-sm text-gray-600">
                <span className="font-medium">Root:</span> {rootAgent.name}
              </div>
            )}
            <button
              onClick={handleSwitchSession}
              className="px-3 py-1.5 rounded-md text-xs font-medium bg-blue-100 hover:bg-blue-200 text-blue-700 transition-colors"
              title="Switch Session"
            >
              Switch Session
            </button>
            <button
              onClick={() => {
                setShowApiKeyModal(true);
              }}
              className="px-3 py-1.5 rounded-md text-xs font-medium bg-gray-100 hover:bg-gray-200 transition-colors"
              title="Change API Key"
            >
              {hasApiKey ? "Change API Key" : "Set API Key"}
            </button>
          </div>
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
              const targetAgent = agents.find((a) => a.id === targetId);
              if (!targetAgent) return;
              // If already connected to this parent, no-op
              if (targetAgent.parent_id === sourceId) return;
              // Prevent cycles: if source is a descendant of target, abort
              const isAncestor = (possibleAncestor: string, nodeId: string): boolean => {
                let current = agents.find((a) => a.id === nodeId)?.parent_id;
                const seen = new Set<string>();
                while (current && !seen.has(current)) {
                  if (current === possibleAncestor) return true;
                  seen.add(current);
                  current = agents.find((a) => a.id === current)?.parent_id || null;
                }
                return false;
              };
              if (isAncestor(targetId, sourceId)) {
                console.warn("Prevented cycle: cannot connect", sourceId, "→", targetId);
                return;
              }
              // If target already has a different parent, re-parent: delete old, then create new
              if (targetAgent.parent_id && targetAgent.parent_id !== sourceId) {
                deleteLinkMutation.mutate({
                  parent_agent_id: targetAgent.parent_id,
                  child_agent_id: targetId,
                });
              }
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
              key={selectedNodeId || rootAgent?.id || "chat-root"}
              agentId={selectedNodeId || undefined}
              rootAgentId={rootAgent?.id}
            />
          )}
        </div>
      </div>
      </>
      )}
    </div>
  );
}
