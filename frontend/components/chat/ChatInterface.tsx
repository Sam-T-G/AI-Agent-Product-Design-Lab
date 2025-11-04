"use client";

import { useState, useEffect, useRef } from "react";
import { createRun, streamRun } from "@/lib/api";
import { useGraphStore } from "@/lib/store";
import { AgentChat, ChatMessage } from "./AgentChat";

interface ChatInterfaceProps {
  agentId?: string;
  rootAgentId?: string; // For backward compatibility
}

export function ChatInterface({ agentId, rootAgentId }: ChatInterfaceProps) {
  // Use agentId if provided, otherwise fallback to rootAgentId
  const activeAgentId = agentId || rootAgentId;
  const { nodes } = useGraphStore();
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState<Array<{ agent_id: string; message: string; timestamp: string }>>([]);
  const [outputs, setOutputs] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [input, setInput] = useState<string>("");
  const [showInternal, setShowInternal] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  
  // Clear chat when agent changes
  useEffect(() => {
    setChatMessages([]);
    setLogs([]);
    setOutputs({});
    setError(null);
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsRunning(false);
  }, [activeAgentId]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // Convert logs and outputs to chat messages
  useEffect(() => {
    if (!activeAgentId) return;
    
    const newMessages: ChatMessage[] = [];

    // Add active agent outputs as agent messages (only the latest)
    const agentOutput = outputs[activeAgentId];
    if (agentOutput && agentOutput.trim()) {
      newMessages.push({
        id: `output-${activeAgentId}`,
        type: "agent",
        agentId: activeAgentId,
        content: agentOutput,
        timestamp: new Date(),
      });
    }

    // Add internal logs as internal messages
    if (showInternal) {
      logs.forEach((log, idx) => {
        // Skip root output logs (we already show the output)
        if (log.message.includes("[ROOT OUTPUT]")) {
          return;
        }

        // Determine if this is an internal communication
        const isInternal = !activeAgentId || log.agent_id !== activeAgentId || 
                           log.message.includes("To the") || 
                           log.message.includes("From ") ||
                           log.message.includes("Child messages") ||
                           log.message.includes("Starting communication iteration") ||
                           log.message.includes("Executing level") ||
                           log.message.includes("Executing ");

        newMessages.push({
          id: `log-${log.agent_id}-${idx}`,
          type: isInternal ? "internal" : "agent",
          agentId: log.agent_id,
          content: log.message,
          timestamp: new Date(log.timestamp),
        });
      });
    }

    // Merge with existing messages, avoiding duplicates
    setChatMessages((prev) => {
      const messageMap = new Map<string, ChatMessage>();
      
      // Keep existing non-output messages (to preserve user messages)
      prev.forEach((msg) => {
        if (msg.type === "user" || (msg.type === "internal" && showInternal)) {
          messageMap.set(msg.id, msg);
        }
      });

      // Add new messages
      newMessages.forEach((msg) => {
        // For output messages, always update; for others, add if new
        if (msg.type === "agent" && msg.id.startsWith("output-")) {
          messageMap.set(msg.id, msg);
        } else if (!messageMap.has(msg.id)) {
          messageMap.set(msg.id, msg);
        }
      });

      // Convert back to array and sort by timestamp
      const sorted = Array.from(messageMap.values()).sort(
        (a, b) => a.timestamp.getTime() - b.timestamp.getTime()
      );

      return sorted;
    });
  }, [logs, outputs, activeAgentId, showInternal]);

  const handleSend = async () => {
    if (!activeAgentId || !input.trim() || isRunning) {
      return;
    }

    const promptText = input.trim();
    
    // Clear input immediately
    setInput("");
    
    // Add user message immediately
    setChatMessages((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        type: "user",
        content: promptText,
        timestamp: new Date(),
      },
    ]);

    setIsRunning(true);
    setError(null);
    
    // Clear previous outputs for this agent only
    setOutputs((prev) => {
      const newOutputs = { ...prev };
      delete newOutputs[activeAgentId];
      return newOutputs;
    });

    try {
      const run = await createRun({
        root_agent_id: activeAgentId,
        input: { 
          prompt: promptText,
          task: promptText 
        },
      });

      // Start SSE streaming
      const eventSource = streamRun(run.id, (event) => {
        if (event.type === "log") {
          setLogs((prev) => [
            ...prev,
            {
              agent_id: event.agent_id || "",
              message: event.data || "",
              timestamp: new Date().toISOString(),
            },
          ]);
        } else if (event.type === "output") {
          setOutputs((prev) => ({
            ...prev,
            [event.agent_id || ""]: event.data || "",
          }));
        } else if (event.type === "output_chunk") {
          setOutputs((prev) => ({
            ...prev,
            [event.agent_id || ""]: (prev[event.agent_id || ""] || "") + (event.data || ""),
          }));
        } else if (event.type === "status") {
          if (event.data === "completed") {
            setIsRunning(false);
          }
        } else if (event.type === "error") {
          setError(event.data || "Unknown error");
          setIsRunning(false);
        }
      });

      eventSourceRef.current = eventSource;

      // Handle connection errors
      eventSource.onerror = () => {
        if (eventSource.readyState === EventSource.CLOSED) {
          if (isRunning) {
            setError("Connection closed. The stream finished or was interrupted.");
            setIsRunning(false);
          }
        } else if (eventSource.readyState === EventSource.CONNECTING) {
          console.log("SSE connecting...");
        } else {
          console.error("SSE error occurred");
          if (isRunning && !error) {
            setError("Connection error occurred. Check your network connection.");
            setIsRunning(false);
          }
        }
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start run");
      setIsRunning(false);
    }
  };

  const handleStop = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsRunning(false);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // Handle Enter key (Cmd/Ctrl + Enter to send, Shift + Enter for new line)
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const activeAgent = activeAgentId ? nodes.find((n) => n.id === activeAgentId) : null;

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <h2 className="text-lg sm:text-xl font-semibold text-gray-900">Chat</h2>
            {activeAgent && (
              <p className="text-xs sm:text-sm text-gray-600 mt-0.5">
                Agent: <span className="font-medium">{activeAgent.data.agent.name}</span>
              </p>
            )}
          </div>
          <label className="flex items-center gap-2 text-xs sm:text-sm text-gray-700 cursor-pointer">
            <input
              type="checkbox"
              checked={showInternal}
              onChange={(e) => setShowInternal(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span>Show Internal</span>
          </label>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-hidden relative bg-gray-50">
        {error && (
          <div className="absolute top-4 left-4 right-4 z-10 bg-red-50 border border-red-200 rounded-lg p-3 shadow-md">
            <p className="text-red-800 text-sm font-medium">Error:</p>
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        )}
        
        <div className="h-full overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
          <AgentChat
            messages={chatMessages}
            showInternal={showInternal}
            rootAgentId={activeAgentId}
            nodes={nodes}
          />
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 bg-white p-3 sm:p-4">
        {!activeAgentId && (
          <div className="mb-3 p-2 sm:p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-xs sm:text-sm text-amber-800">
              No agent selected. Click on an agent to start chatting.
            </p>
          </div>
        )}
        <div className="flex items-end gap-2 sm:gap-3">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={activeAgentId ? "Type your message... (Cmd/Ctrl + Enter to send)" : "Select an agent to start chatting..."}
              disabled={isRunning || !activeAgentId}
              rows={1}
              className="w-full px-3 sm:px-4 py-2 sm:py-3 pr-10 sm:pr-12 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-900 resize-none disabled:bg-gray-50 disabled:cursor-not-allowed placeholder:text-gray-400 overflow-hidden"
              style={{ minHeight: "44px", maxHeight: "200px" }}
            />
            <div className="absolute bottom-2 sm:bottom-3 right-2 sm:right-3 text-xs text-gray-400 hidden sm:block">
              {isRunning ? "..." : "⌘⏎"}
            </div>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <button
              onClick={handleSend}
              disabled={!input.trim() || isRunning || !activeAgentId}
              className="px-4 sm:px-6 py-2 sm:py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl text-xs sm:text-sm font-medium shadow-sm transition-colors"
            >
              {isRunning ? (
                <span className="flex items-center gap-1.5 sm:gap-2">
                  <span className="w-3 h-3 sm:w-4 sm:h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span className="hidden sm:inline">Sending...</span>
                </span>
              ) : (
                "Send"
              )}
            </button>
            {isRunning && (
              <button
                onClick={handleStop}
                className="px-3 sm:px-4 py-2 sm:py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs sm:text-sm font-medium shadow-sm transition-colors"
              >
                Stop
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

