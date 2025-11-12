"use client";

import { useState, useEffect, useRef } from "react";
import { Agent, AgentCreate } from "@/lib/types";
import { updateAgent } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import { ConfirmModal } from "@/components/modal/ConfirmModal";

interface AgentDrawerProps {
  agent: Agent | null;
  onClose: () => void;
  onSave?: (agent: Agent) => void;
  onDelete?: (agentId: string) => void;
  agents?: Agent[];
}

export function AgentDrawer({ agent, onClose, onSave, onDelete, agents = [] }: AgentDrawerProps) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<Partial<AgentCreate>>({
    name: "",
    role: "",
    system_prompt: "",
    parameters: {
      temperature: 0.7,
      max_tokens: 1000,
      model: "gemini-2.5-flash",
    },
  });
  const [isSaving, setIsSaving] = useState(false);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  useEffect(() => {
    if (agent) {
      setFormData({
        name: agent.name,
        role: agent.role,
        system_prompt: agent.system_prompt,
        parameters: agent.parameters || {
          temperature: 0.7,
          max_tokens: 1000,
          model: "gemini-2.5-flash",
        },
        photo_injection_enabled: agent.photo_injection_enabled ?? false,
        photo_injection_features: agent.photo_injection_features || [],
      });
    }
  }, [agent]);

  const currentAgentId = agent?.id;

  // Autosave with debounce when formData changes
  useEffect(() => {
    if (!currentAgentId) return;
    
    // Skip autosave if formData is empty or invalid
    if (!formData.name || !formData.name.trim()) {
      return;
    }
    
    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    debounceTimerRef.current = setTimeout(async () => {
      try {
        // Check if session ID exists before attempting save
        if (typeof window !== "undefined") {
          const sessionId = localStorage.getItem("SESSION_ID");
          if (!sessionId) {
            console.warn("Autosave skipped: No session ID available");
            return;
          }
        }
        
        await updateAgent(currentAgentId, formData);
      } catch (e) {
        console.error("Autosave failed:", e);
        // Don't show alert for autosave failures - just log
      }
    }, 600);
    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    };
  }, [currentAgentId, formData]);

  const handleSave = async () => {
    if (!agent) return;
    
    // Validate session ID before attempting save
    if (typeof window !== "undefined") {
      const sessionId = localStorage.getItem("SESSION_ID");
      if (!sessionId) {
        alert("No session selected. Please select a session first.");
        return;
      }
    }
    
    setIsSaving(true);
    try {
      const updated = await updateAgent(agent.id, formData);
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      onSave?.(updated);
      onClose();
    } catch (error) {
      console.error("Failed to save agent:", error);
      const errorMessage = error instanceof Error ? error.message : "Failed to save agent";
      alert(`Failed to save agent: ${errorMessage}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteClick = () => {
    setShowDeleteModal(true);
  };

  const handleConfirmDelete = () => {
    if (agent && onDelete) {
      onDelete(agent.id);
      setShowDeleteModal(false);
      onClose();
    }
  };

  const handleCancelDelete = () => {
    setShowDeleteModal(false);
  };

  // Check if agent has children
  const hasChildren = agent ? agents.some((a) => a.parent_id === agent.id) : false;

  if (!agent) {
    return (
      <div className="w-96 bg-white border-l border-gray-200 p-6">
        <p className="text-gray-700">No agent selected</p>
      </div>
    );
  }

  return (
    <div className="w-full bg-white flex flex-col h-full">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Edit Agent</h2>
          <button
            onClick={onClose}
            className="text-gray-700 hover:text-gray-900"
          >
            ✕
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Name
          </label>
          <input
            type="text"
            value={formData.name || ""}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
          />
        </div>

        {/* Role */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Role
          </label>
          <input
            type="text"
            value={formData.role || ""}
            onChange={(e) => setFormData({ ...formData, role: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
          />
        </div>

        {/* System Prompt */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            System Prompt
          </label>
          <textarea
            value={formData.system_prompt || ""}
            onChange={(e) =>
              setFormData({ ...formData, system_prompt: e.target.value })
            }
            rows={8}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm text-gray-900 placeholder:text-gray-500"
            placeholder="Describe this agent's role, capabilities, and behavior..."
          />
        </div>

        {/* Parameters */}
        <div className="space-y-3">
          <label className="block text-sm font-medium text-gray-700">
            Parameters
          </label>
          
          {/* Temperature */}
          <div>
            <label className="block text-xs text-gray-800 mb-1">
              Temperature: {formData.parameters?.temperature || 0.7}
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={formData.parameters?.temperature || 0.7}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  parameters: {
                    ...formData.parameters,
                    temperature: parseFloat(e.target.value),
                  },
                })
              }
              className="w-full"
            />
          </div>

          {/* Max Tokens */}
          <div>
            <label className="block text-xs text-gray-800 mb-1">
              Max Tokens
            </label>
            <input
              type="number"
              min="100"
              max="4000"
              step="100"
              value={formData.parameters?.max_tokens || 1000}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  parameters: {
                    ...formData.parameters,
                    max_tokens: parseInt(e.target.value),
                  },
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900"
            />
          </div>

          {/* Model */}
          <div>
            <label className="block text-xs text-gray-800 mb-1">Model</label>
            <select
              value={formData.parameters?.model || "gemini-2.5-flash"}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  parameters: {
                    ...formData.parameters,
                    model: e.target.value,
                  },
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900"
            >
              <option value="gemini-2.5-flash">Gemini 2.5 Flash (Recommended)</option>
              <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
            </select>
          </div>
        </div>

        {/* Photo Injection Configuration */}
        <div className="space-y-3 border-t border-gray-200 pt-4">
          <label className="block text-sm font-medium text-gray-700">
            Photo Injection
          </label>
          <p className="text-xs text-gray-600 mb-3">
            Enable this agent to accept and process images. Students can upload photos directly when prompting this agent.
          </p>
          
          {/* Enable Photo Injection */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="photo-injection-enabled"
              checked={formData.photo_injection_enabled || false}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  photo_injection_enabled: e.target.checked,
                })
              }
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <label htmlFor="photo-injection-enabled" className="text-sm text-gray-700">
              Enable photo injection for this agent
            </label>
          </div>

          {/* Custom Features */}
          {formData.photo_injection_enabled && (
            <div>
              <label className="block text-xs text-gray-800 mb-2">
                Custom Features (comma-separated)
              </label>
              <input
                type="text"
                value={(formData.photo_injection_features || []).join(", ")}
                onChange={(e) => {
                  const features = e.target.value
                    .split(",")
                    .map((f) => f.trim())
                    .filter((f) => f.length > 0);
                  setFormData({
                    ...formData,
                    photo_injection_features: features,
                  });
                }}
                placeholder="e.g., object_detection, text_extraction, style_analysis"
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-900 placeholder:text-gray-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Define custom capabilities for this photo-injection agent. These will be included in the system prompt.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="p-6 border-t border-gray-200 space-y-2">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white py-2 px-4 rounded-md font-medium transition-colors"
        >
          {isSaving ? "Saving..." : "Save"}
        </button>
        <button
          onClick={onClose}
          className="w-full bg-gray-200 hover:bg-gray-300 text-gray-700 py-2 px-4 rounded-md font-medium transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleDeleteClick}
          className="w-full bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded-md font-medium transition-colors mt-4"
        >
          Delete Agent
        </button>
      </div>

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={showDeleteModal}
        title="Delete Agent"
        message={
          hasChildren
            ? `Warning: "${agent.name}" has child agents. Deleting it will also remove all child agents and their connections. Are you sure you want to continue?`
            : `Are you sure you want to delete "${agent?.name}"? This action cannot be undone and will remove all connections.`
        }
        confirmText="Delete"
        cancelText="Cancel"
        onConfirm={handleConfirmDelete}
        onCancel={handleCancelDelete}
        variant="danger"
      />
    </div>
  );
}
