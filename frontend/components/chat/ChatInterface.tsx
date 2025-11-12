"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Image from "next/image";
import { createRun, streamRun } from "@/lib/api";
import { useGraphStore } from "@/lib/store";
import { AgentStatus } from "@/lib/types";
import { AgentChat, ChatMessage } from "./AgentChat";

interface ChatInterfaceProps {
	agentId?: string;
	rootAgentId?: string; // For backward compatibility
}

export function ChatInterface({ agentId, rootAgentId }: ChatInterfaceProps) {
	// Use agentId if provided, otherwise fallback to rootAgentId
	const activeAgentId = agentId || rootAgentId;
	const nodes = useGraphStore((state) => state.nodes);
	const setAgentStatus = useGraphStore((state) => state.setAgentStatus);
	const recordDelegation = useGraphStore((state) => state.recordDelegation);
	const clearDelegation = useGraphStore((state) => state.clearDelegation);

	const [isRunning, setIsRunning] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [input, setInput] = useState<string>("");
	const [showInternal, setShowInternal] = useState(true); // Default to true to show all agent outputs
	const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
	const [uploadedImages, setUploadedImages] = useState<
		Array<{ file: File; preview: string }>
	>([]);
	const eventSourceRef = useRef<EventSource | null>(null);
	const messagesEndRef = useRef<HTMLDivElement>(null);
	const inputRef = useRef<HTMLTextAreaElement>(null);
	const fileInputRef = useRef<HTMLInputElement>(null);
	const currentStreamingMessageIdRef = useRef<string | null>(null);
const conversationHistoryRef = useRef<string[]>([]); // Track conversation for context
const messageIdCounterRef = useRef(0); // Unique counter for message IDs
const finalizedAgentsRef = useRef<Set<string>>(new Set()); // Track finalized agents to prevent duplicates
	const accumulatedOutputByAgentRef = useRef<Map<string, string>>(new Map()); // Track accumulated output per agent

	const agentStatuses: AgentStatus[] = [
		"idle",
		"analyzing",
		"executing",
		"completed",
		"error",
	];

	const isAgentStatus = (value: unknown): value is AgentStatus =>
		typeof value === "string" && agentStatuses.includes(value as AgentStatus);

	const DELEGATION_HIGHLIGHT_MS = 2500;

	const resolveAgentName = useCallback(
		(id: string | undefined) =>
			id ? nodes.find((n) => n.id === id)?.data.agent.name || "Agent" : "Agent",
		[nodes]
	);

	const appendInternalMessage = useCallback(
		(content: string) => {
			setChatMessages((prev) => [
				...prev,
				{
					id: `internal-${Date.now()}-${prev.length}`,
					type: "internal",
					content,
					timestamp: new Date(),
				},
			]);
		},
		[]
	);

	// Auto-scroll to bottom when messages change
	useEffect(() => {
		messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
	}, [chatMessages]);

	// Handle streaming output chunks - build message incrementally
	const handleStreamingChunk = useCallback(
		(agentId: string, chunk: string) => {
			setChatMessages((prev) => {
				const messageId = `agent-${agentId}-streaming`;
				const existingIndex = prev.findIndex((msg) => msg.id === messageId);

				if (existingIndex >= 0) {
					// Update existing streaming message
					const updated = [...prev];
					updated[existingIndex] = {
						...updated[existingIndex],
						content: updated[existingIndex].content + chunk,
						timestamp: new Date(), // Update timestamp to show it's active
					};
					return updated;
				} else {
					// Create new streaming message
					const agentName = resolveAgentName(agentId);
					return [
						...prev,
						{
							id: messageId,
							type: "agent",
							agentId: agentId,
							agentName: agentName,
							content: chunk,
							timestamp: new Date(),
						},
					];
				}
			});
			currentStreamingMessageIdRef.current = `agent-${agentId}-streaming`;
		},
		[resolveAgentName]
	);

	// Handle final output - convert streaming message to final message
	const handleFinalOutput = useCallback(
		(agentId: string, fullOutput: string) => {
			// Create a content hash for better duplicate detection
			const contentHash = fullOutput.slice(0, 50) + fullOutput.length;
			const finalizationKey = `${agentId}-${contentHash}`;

			// Prevent duplicate finalizations for the same agent + content
			if (finalizedAgentsRef.current.has(finalizationKey)) {
				return; // Already finalized this exact output
			}
			finalizedAgentsRef.current.add(finalizationKey);

			setChatMessages((prev) => {
				const streamingId = `agent-${agentId}-streaming`;
				// Use counter + timestamp for truly unique IDs
				messageIdCounterRef.current += 1;
				const finalId = `agent-${agentId}-${Date.now()}-${
					messageIdCounterRef.current
				}`;

				// Remove streaming message and add final message
				const filtered = prev.filter((msg) => msg.id !== streamingId);

				// Check if final message already exists with same content (double-check)
				const alreadyExists = filtered.some(
					(msg) =>
						msg.agentId === agentId &&
						msg.content === fullOutput &&
						msg.type === "agent"
				);
				if (alreadyExists) {
					return filtered; // Don't add duplicate
				}

			const agentName = resolveAgentName(agentId);

			return [
				...filtered,
				{
					id: finalId,
					type: "agent",
					agentId: agentId,
					agentName: agentName,
					content: fullOutput,
					timestamp: new Date(),
				},
			];
			});

			// Clear streaming message ref if this was the active one
			if (
				currentStreamingMessageIdRef.current === `agent-${agentId}-streaming`
			) {
				currentStreamingMessageIdRef.current = null;
			}

			// Add to conversation history for context (only once per unique output)
			if (!conversationHistoryRef.current.includes(fullOutput)) {
				conversationHistoryRef.current.push(fullOutput);
			}
		},
		[resolveAgentName]
	);

	const handleSend = async () => {
		console.log("🚀 [CHAT] handleSend called", {
			activeAgentId,
			hasInput: !!input.trim(),
			imageCount: uploadedImages.length,
			isRunning,
		});

		// Allow sending with just images (no text input required)
		if (
			!activeAgentId ||
			(!input.trim() && uploadedImages.length === 0) ||
			isRunning
		) {
			console.log("⚠️ [CHAT] handleSend validation failed", {
				activeAgentId,
				hasInput: !!input.trim(),
				imageCount: uploadedImages.length,
				isRunning,
			});
			return;
		}

		const promptText = input.trim() || "Process these images";

		// Double-check we're not already running (race condition protection)
		if (isRunning) {
			console.log("⚠️ [CHAT] Already running, aborting");
			return;
		}

		// Clear input immediately
		setInput("");

		// Add user message immediately
		const userMessageId = `user-${Date.now()}`;
		setChatMessages((prev) => [
			...prev,
			{
				id: userMessageId,
				type: "user",
				content: promptText,
				timestamp: new Date(),
			},
		]);

		// Add to conversation history
		conversationHistoryRef.current.push(promptText);

		setIsRunning(true);
		setError(null);

		console.log("📝 [CHAT] Creating run", {
			agentId: activeAgentId,
			promptLength: promptText.length,
		});

		try {
			// Convert uploaded images to base64
			const imageBase64List: string[] = [];
			for (const img of uploadedImages) {
				const reader = new FileReader();
				const base64Promise = new Promise<string>((resolve, reject) => {
					reader.onload = () => {
						const result = reader.result as string;
						// Remove data URL prefix if present
						const base64 = result.includes(",") ? result.split(",")[1] : result;
						resolve(base64);
					};
					reader.onerror = reject;
				});
				reader.readAsDataURL(img.file);
				const base64 = await base64Promise;
				imageBase64List.push(base64);
			}

			// Build conversation context for better continuity
			const conversationContext = conversationHistoryRef.current
				.slice(-5)
				.join("\n\n");
			const enhancedPrompt =
				conversationHistoryRef.current.length > 1
					? `${conversationContext}\n\nUser: ${promptText}`
					: promptText;

			// Get session_id from localStorage
			const sessionId =
				typeof window !== "undefined"
					? localStorage.getItem("SESSION_ID")
					: null;
			const run = await createRun(
				{
					root_agent_id: activeAgentId,
					input: {
						prompt: enhancedPrompt,
						task: promptText,
						conversation_history: conversationHistoryRef.current.slice(-3), // Last 3 exchanges
					},
					images: imageBase64List.length > 0 ? imageBase64List : undefined,
				},
				sessionId || undefined
			);

			console.log("✅ [CHAT] Run created", { runId: run.id, sessionId });

			// Clear images after sending
			setUploadedImages([]);

			// Clear accumulated output tracking when starting new run
			accumulatedOutputByAgentRef.current.clear();

			// Clear finalized agents tracking when starting new run
			finalizedAgentsRef.current.clear();

			// Start SSE streaming
			console.log("🌊 [CHAT] Starting SSE stream", { runId: run.id });

			const eventSource = streamRun(
				run.id,
				(event) => {
					console.log("📨 [CHAT] SSE event received", {
						type: event.type,
						agentId: event.agent_id?.substring(0, 20),
						dataLength: typeof event.data === "string" ? event.data.length : 0,
					});

				if (event.type === "output_chunk") {
					const chunk =
						(typeof event.data === "string" ? event.data : "") || "";
						const agentId = event.agent_id || activeAgentId;

						// Accumulate per agent
						const current =
							accumulatedOutputByAgentRef.current.get(agentId) || "";
						accumulatedOutputByAgentRef.current.set(agentId, current + chunk);

						handleStreamingChunk(agentId, chunk);
					} else if (event.type === "output") {
						// Final output received - this is the authoritative output
						const finalOutput =
							(typeof event.data === "string" ? event.data : "") || "";
						const agentId = event.agent_id || activeAgentId;

						// Update accumulated output for this agent
						accumulatedOutputByAgentRef.current.set(agentId, finalOutput);

						// Always use the final output from the "output" event
						if (finalOutput.trim()) {
							handleFinalOutput(agentId, finalOutput);
						}
				} else if (event.type === "status") {
					if (event.agent_id && isAgentStatus(event.data)) {
						setAgentStatus(event.agent_id, event.data);
					}
					if (event.data === "completed") {
						// On completion, only finalize if we haven't received an "output" event yet
							// Check if we have accumulated output for the active agent that hasn't been finalized
							const activeAgentAccumulated =
								accumulatedOutputByAgentRef.current.get(activeAgentId) || "";

							if (
								activeAgentAccumulated.trim() &&
								currentStreamingMessageIdRef.current &&
								currentStreamingMessageIdRef.current ===
									`agent-${activeAgentId}-streaming`
							) {
								// Only finalize if we still have a streaming message (meaning no "output" event was received)
								handleFinalOutput(activeAgentId, activeAgentAccumulated);
							}
							setIsRunning(false);
						}
				} else if (event.type === "delegation") {
					const payload = (event.data || {}) as {
						from?: string;
						to?: string;
						label?: string;
					};
					if (payload.from && payload.to) {
						recordDelegation(payload.from, payload.to);
						setTimeout(() => {
							clearDelegation(payload.from!, payload.to!);
						}, DELEGATION_HIGHLIGHT_MS);
						const fromName = resolveAgentName(payload.from);
						const toName = resolveAgentName(payload.to);
						appendInternalMessage(
							payload.label || `${fromName} → ${toName}`
						);
					}
				} else if (event.type === "error") {
						const errorMsg =
							(typeof event.data === "string" ? event.data : "Unknown error") ||
							"Unknown error";
						console.error("❌ [CHAT] Error event received", {
							error: errorMsg,
						});
						setError(errorMsg);
						setIsRunning(false);
						// Remove streaming message on error
						if (currentStreamingMessageIdRef.current) {
							setChatMessages((prev) =>
								prev.filter(
									(msg) => msg.id !== currentStreamingMessageIdRef.current
								)
							);
							currentStreamingMessageIdRef.current = null;
						}
					}
				},
				sessionId || undefined
			);

			eventSourceRef.current = eventSource;

			// Handle connection errors
			eventSource.onerror = (event) => {
				console.error("❌ [CHAT] SSE error", {
					event,
					readyState: eventSource.readyState,
					isRunning,
				});

				if (eventSource.readyState === EventSource.CLOSED) {
					if (isRunning) {
						// Try to finalize any accumulated output
						const finalAccumulated =
							accumulatedOutputByAgentRef.current.get(activeAgentId) || "";
						if (
							finalAccumulated.trim() &&
							currentStreamingMessageIdRef.current
						) {
							const finalizationKey = `${activeAgentId}-${finalAccumulated.length}`;
							if (!finalizedAgentsRef.current.has(finalizationKey)) {
								handleFinalOutput(activeAgentId, finalAccumulated);
							}
						}

						setError(
							"Connection closed. The stream finished or was interrupted."
						);
						setIsRunning(false);
					}
				} else if (eventSource.readyState === EventSource.CONNECTING) {
					console.log("SSE reconnecting...");
					// Don't set error during reconnection attempts
				} else {
					console.error("SSE error occurred, state:", eventSource.readyState);
					if (isRunning) {
						// Try to finalize any accumulated output before showing error
						const finalAccumulated =
							accumulatedOutputByAgentRef.current.get(activeAgentId) || "";
						if (
							finalAccumulated.trim() &&
							currentStreamingMessageIdRef.current
						) {
							const finalizationKey = `${activeAgentId}-${finalAccumulated.length}`;
							if (!finalizedAgentsRef.current.has(finalizationKey)) {
								handleFinalOutput(activeAgentId, finalAccumulated);
							}
						}

						setError(
							"Connection error occurred. Check your network connection and try again."
						);
						setIsRunning(false);
					}
				}
			};
		} catch (err) {
			console.error("❌ [CHAT] Failed to start run", { error: err });
			setError(err instanceof Error ? err.message : "Failed to start run");
			setIsRunning(false);
			// Remove streaming message on error
			if (currentStreamingMessageIdRef.current) {
				setChatMessages((prev) =>
					prev.filter((msg) => msg.id !== currentStreamingMessageIdRef.current)
				);
				currentStreamingMessageIdRef.current = null;
			}
		}
	};

	const handleStop = () => {
		if (eventSourceRef.current) {
			eventSourceRef.current.close();
			eventSourceRef.current = null;
		}
		// Finalize current streaming message if exists
		if (currentStreamingMessageIdRef.current) {
			setChatMessages((prev) => {
				const streamingId = currentStreamingMessageIdRef.current!;
				const streamingMsg = prev.find((msg) => msg.id === streamingId);
				if (streamingMsg) {
					// Convert to final message
					const filtered = prev.filter((msg) => msg.id !== streamingId);
					return [
						...filtered,
						{
							...streamingMsg,
							id: `agent-${streamingMsg.agentId}-${Date.now()}`,
						},
					];
				}
				return prev;
			});
			currentStreamingMessageIdRef.current = null;
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
			inputRef.current.style.height = `${Math.min(
				inputRef.current.scrollHeight,
				200
			)}px`;
		}
	}, [input]);

	const activeAgent = activeAgentId
		? nodes.find((n) => n.id === activeAgentId)
		: null;
	const isPhotoInjectionEnabled =
		activeAgent?.data.agent.photo_injection_enabled ?? false;

	// Handle image upload
	const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
		const files = Array.from(e.target.files || []);
		if (files.length === 0) return;

		files.forEach((file) => {
			if (!file.type.startsWith("image/")) {
				alert(`${file.name} is not an image file.`);
				return;
			}

			// Create preview
			const reader = new FileReader();
			reader.onload = () => {
				setUploadedImages((prev) => [
					...prev,
					{ file, preview: reader.result as string },
				]);
			};
			reader.readAsDataURL(file);
		});

		// Reset input
		if (fileInputRef.current) {
			fileInputRef.current.value = "";
		}
	};

	// Remove image
	const handleRemoveImage = (index: number) => {
		setUploadedImages((prev) => prev.filter((_, i) => i !== index));
	};

	return (
		<div className="h-full flex flex-col bg-white">
			{/* Header */}
			<div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
				<div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
					<div>
						<h2 className="text-lg sm:text-xl font-semibold text-gray-900">
							Chat
						</h2>
						{activeAgent && (
							<p className="text-xs sm:text-sm text-gray-600 mt-0.5">
								Agent:{" "}
								<span className="font-medium">
									{activeAgent.data.agent.name}
								</span>
							</p>
						)}
					</div>
					<div className="flex items-center gap-3">
						<label className="flex items-center gap-2 text-xs sm:text-sm text-gray-700 cursor-pointer">
							<input
								type="checkbox"
								checked={showInternal}
								onChange={(e) => setShowInternal(e.target.checked)}
								className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
							/>
							<span>Show Internal</span>
						</label>
						{chatMessages.length > 0 && (
							<button
								onClick={() => {
									setChatMessages([]);
									setError(null);
									setUploadedImages([]);
									conversationHistoryRef.current = [];
									currentStreamingMessageIdRef.current = null;
									if (eventSourceRef.current) {
										eventSourceRef.current.close();
										eventSourceRef.current = null;
									}
									setIsRunning(false);
								}}
								className="px-2 py-1 text-xs text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
								title="Clear conversation">
								Clear
							</button>
						)}
					</div>
				</div>
			</div>

			{/* Chat Messages */}
			<div className="flex-1 overflow-hidden relative bg-gray-50">
				{error && (
					<div className="absolute top-4 left-4 right-4 z-10 bg-red-50 border border-red-200 rounded-lg p-3 shadow-md">
						<p className="text-red-800 text-sm font-medium">Error:</p>
						<p className="text-red-600 text-sm">{error}</p>
						<button
							onClick={() => setError(null)}
							className="mt-2 text-xs text-red-600 hover:text-red-800 underline">
							Dismiss
						</button>
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

				{/* Image Preview */}
				{uploadedImages.length > 0 && (
					<div className="mb-3 flex flex-wrap gap-2">
							{uploadedImages.map((img, idx) => (
								<div key={idx} className="relative group">
									<Image
										src={img.preview}
										alt={`Upload ${idx + 1}`}
										width={80}
										height={80}
										className="w-20 h-20 object-cover rounded-lg border border-gray-300"
										unoptimized
									/>
								<button
									onClick={() => handleRemoveImage(idx)}
									className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
									×
								</button>
							</div>
						))}
					</div>
				)}

				<div className="flex items-end gap-2 sm:gap-3">
					<div className="flex-1 relative">
						<textarea
							ref={inputRef}
							value={input}
							onChange={(e) => setInput(e.target.value)}
							onKeyDown={handleKeyDown}
							placeholder={
								activeAgentId
									? "Type your message... (Cmd/Ctrl + Enter to send)"
									: "Select an agent to start chatting..."
							}
							disabled={isRunning || !activeAgentId}
							rows={1}
							className="w-full px-3 sm:px-4 py-2 sm:py-3 pr-10 sm:pr-12 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-900 resize-none disabled:bg-gray-50 disabled:cursor-not-allowed placeholder:text-gray-400 overflow-hidden"
							style={{ minHeight: "44px", maxHeight: "200px" }}
						/>
						<div className="absolute bottom-2 sm:bottom-3 right-2 sm:right-3 text-xs text-gray-400 hidden sm:block">
							{isRunning ? "..." : "⌘⏎"}
						</div>
					</div>
					<div className="flex gap-2 shrink-0">
						{/* Image Upload Button (only for photo-injection-enabled agents) */}
						{isPhotoInjectionEnabled && (
							<>
								<input
									ref={fileInputRef}
									type="file"
									accept="image/*"
									multiple
									onChange={handleImageUpload}
									className="hidden"
								/>
								<button
									onClick={() => fileInputRef.current?.click()}
									disabled={isRunning || !activeAgentId}
									className="px-3 sm:px-4 py-2 sm:py-3 bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:cursor-not-allowed text-gray-700 rounded-xl text-xs sm:text-sm font-medium shadow-sm transition-colors"
									title="Upload images">
									📷
								</button>
							</>
						)}
						<button
							onClick={handleSend}
							disabled={
								(!input.trim() && uploadedImages.length === 0) ||
								isRunning ||
								!activeAgentId
							}
							className="px-4 sm:px-6 py-2 sm:py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl text-xs sm:text-sm font-medium shadow-sm transition-colors">
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
								className="px-3 sm:px-4 py-2 sm:py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs sm:text-sm font-medium shadow-sm transition-colors">
								Stop
							</button>
						)}
					</div>
				</div>
			</div>
		</div>
	);
}
