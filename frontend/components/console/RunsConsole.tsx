"use client";

import { useState, useEffect, useRef } from "react";
import { createRun, streamRun } from "@/lib/api";
import { useRunStore } from "@/lib/store";
import { useGraphStore } from "@/lib/store";
import { AgentChat, ChatMessage } from "@/components/chat/AgentChat";

export function RunsConsole() {
  const { selectedNodeId, nodes } = useGraphStore();
  const { currentRunId, setCurrentRun } = useRunStore();
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState<Array<{ agent_id: string; message: string; timestamp: string }>>([]);
  const [outputs, setOutputs] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [initialPrompt, setInitialPrompt] = useState<string>("");
  const [showInternal, setShowInternal] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const lastUserMessageRef = useRef<string>("");

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // Convert logs and outputs to chat messages
  useEffect(() => {
    const newMessages: ChatMessage[] = [];

    // Add root agent outputs as agent messages (only the latest)
    const rootOutput = outputs[selectedNodeId || ""];
    if (rootOutput && rootOutput.trim()) {
      newMessages.push({
        id: `output-${selectedNodeId}`,
        type: "agent",
        agentId: selectedNodeId || undefined,
        content: rootOutput,
        timestamp: new Date(),
      });
    }

    // Add internal logs as internal messages (only when toggle is on)
    if (showInternal) {
      logs.forEach((log, idx) => {
        // Skip root output logs (we already show the output)
        if (log.message.includes("[ROOT OUTPUT]")) {
          return;
        }

        // Determine if this is an internal communication
        const isInternal = log.agent_id !== selectedNodeId || 
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
  }, [logs, outputs, selectedNodeId, showInternal]);

  const handleStartRun = async () => {
    if (!selectedNodeId) {
      alert("Please select a root agent node");
      return;
    }

    const promptText = initialPrompt || "Execute agent workflow";
    
    setIsRunning(true);
    setLogs([]);
    setOutputs({});
    setError(null);
    lastUserMessageRef.current = promptText;
    
    // Add user message immediately
    setChatMessages((prev) => {
      // Remove any existing agent messages to start fresh, but keep user messages
      const userMessages = prev.filter((msg) => msg.type === "user");
      return [
        ...userMessages,
        {
          id: `user-${Date.now()}`,
          type: "user",
          content: promptText,
          timestamp: new Date(),
        },
      ];
    });

    try {
      const run = await createRun({
        root_agent_id: selectedNodeId,
        input: { 
          prompt: promptText,
          task: promptText 
        },
      });

      setCurrentRun(run.id);

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
          // For "output" events, replace the output (not append) to show final output
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
        // Check connection state
        if (eventSource.readyState === EventSource.CLOSED) {
          // Connection closed - only show error if we're still expecting to run
          if (isRunning) {
            setError("Connection closed. The stream finished or was interrupted.");
            setIsRunning(false);
          }
        } else if (eventSource.readyState === EventSource.CONNECTING) {
          // Still connecting, don't show error yet
          console.log("SSE connecting...");
        } else {
          // Other error state (OPEN but error occurred)
          console.error("SSE error occurred");
          // EventSource.onerror doesn't provide error details
          // Only set error if we don't already have one and we're still running
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

  const selectedAgent = nodes.find((n) => n.id === selectedNodeId);

  return (
    <div className="bg-white border-t border-gray-200 flex flex-col" style={{ height: "500px" }}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="font-semibold text-gray-900">Agent Chat</h3>
            {selectedAgent && (
              <p className="text-sm text-gray-600">
                Root Agent: <span className="font-medium">{selectedAgent.data.agent.name}</span>
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* Toggle for internal communications */}
            <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={showInternal}
                onChange={(e) => setShowInternal(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-xs">Show Internal</span>
            </label>
            <div className="space-x-2">
              <button
                onClick={handleStartRun}
                disabled={isRunning || !selectedNodeId}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg text-sm font-medium shadow-sm transition-colors"
              >
                {isRunning ? "Running..." : "Start Run"}
              </button>
              {isRunning && (
                <button
                  onClick={handleStop}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium shadow-sm transition-colors"
                >
                  Stop
                </button>
              )}
            </div>
          </div>
        </div>
        
        {/* Prompt Input */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Your Message
          </label>
          <textarea
            value={initialPrompt}
            onChange={(e) => setInitialPrompt(e.target.value)}
            placeholder="Enter your prompt or task for the agent ecosystem..."
            disabled={isRunning}
            rows={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-900 resize-none disabled:bg-gray-100 disabled:cursor-not-allowed placeholder:text-gray-400"
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && !isRunning && selectedNodeId) {
                e.preventDefault();
                handleStartRun();
              }
            }}
          />
          <p className="text-xs text-gray-500 mt-1">
            Press Cmd/Ctrl + Enter to send
          </p>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-hidden relative bg-gray-50">
        {error && (
          <div className="absolute top-4 left-4 right-4 z-10 bg-red-50 border border-red-200 rounded-lg p-3 shadow-md">
            <p className="text-red-800 text-sm font-medium">Error:</p>
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        )}
        
        <AgentChat
          messages={chatMessages}
          showInternal={showInternal}
          rootAgentId={selectedNodeId || undefined}
          nodes={nodes}
        />
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}


