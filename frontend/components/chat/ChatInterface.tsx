"use client";

import { useState, useEffect, useRef, useCallback } from "react";
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
	const [error, setError] = useState<string | null>(null);
	const [input, setInput] = useState<string>("");
	const [showInternal, setShowInternal] = useState(false);
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
	const previousAgentIdRef = useRef<string | undefined>(undefined);
	const shouldClearChatRef = useRef(false);
	// Typing animation
	const typingQueueRef = useRef<string[]>([]);
	const typingTimerRef = useRef<number | null>(null);
	const typingTargetIdRef = useRef<string | null>(null);
	const [typingSpeedMs] = useState<number>(12); // lower = faster

	// Clear chat when agent changes - use ref flag to avoid React warning
	useEffect(() => {
		if (
			previousAgentIdRef.current !== undefined &&
			previousAgentIdRef.current !== activeAgentId
		) {
			shouldClearChatRef.current = true;
		}
		previousAgentIdRef.current = activeAgentId;
	}, [activeAgentId]);

	// Separate effect to handle clearing (React best practice)
	useEffect(() => {
		if (shouldClearChatRef.current) {
			shouldClearChatRef.current = false;
			// Defer to avoid synchronous setState inside effect (linter rule)
			setTimeout(() => {
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
			}, 0);
		}
	}, [activeAgentId]);

	// Auto-scroll to bottom when messages change
	useEffect(() => {
		messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
	}, [chatMessages]);

	// Handle streaming output chunks - build message incrementally
	const handleStreamingChunk = useCallback(
		(agentId: string, chunk: string) => {
			const messageId = `agent-${agentId}-streaming`;
			// Ensure a streaming message exists
			setChatMessages((prev) => {
				const existingIndex = prev.findIndex((m) => m.id === messageId);
				if (existingIndex >= 0) return prev;
				const agentName =
					nodes.find((n) => n.id === agentId)?.data.agent.name || "Agent";
				return [
					...prev,
					{
						id: messageId,
						type: "agent",
						agentId,
						agentName,
						content: "",
						timestamp: new Date(),
					},
				];
			});
			// Queue characters for typing animation
			typingQueueRef.current.push(chunk);
			typingTargetIdRef.current = messageId;
			currentStreamingMessageIdRef.current = messageId;
			// Start timer if not running
			if (typingTimerRef.current === null) {
				typingTimerRef.current = window.setInterval(() => {
					const targetId = typingTargetIdRef.current;
					if (!targetId) return;
					const buffer = typingQueueRef.current;
					if (buffer.length === 0) return; // nothing to type
					// Take one character at a time from the head of the queue
					let nextChar = "";
					if (buffer[0].length > 0) {
						nextChar = buffer[0].charAt(0);
						buffer[0] = buffer[0].slice(1);
					} else {
						buffer.shift();
						return;
					}
					setChatMessages((prev) => {
						const idx = prev.findIndex((m) => m.id === targetId);
						if (idx === -1) return prev;
						const updated = [...prev];
						updated[idx] = {
							...updated[idx],
							content: updated[idx].content + nextChar,
							timestamp: new Date(),
						};
						return updated;
					});
				}, typingSpeedMs);
			}
		},
		[nodes, typingSpeedMs]
	);

	// Handle final output - convert streaming message to final message
	const handleFinalOutput = useCallback(
		(agentId: string, fullOutput: string) => {
			setChatMessages((prev) => {
				const streamingId = `agent-${agentId}-streaming`;
				const finalId = `agent-${agentId}-${Date.now()}`;

				// Remove streaming message and add final message
				const filtered = prev.filter((msg) => msg.id !== streamingId);
				const agentName =
					nodes.find((n) => n.id === agentId)?.data.agent.name || "Agent";

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
			currentStreamingMessageIdRef.current = null;
			// Stop typing timer and clear queue
			if (typingTimerRef.current !== null) {
				window.clearInterval(typingTimerRef.current);
				typingTimerRef.current = null;
			}
			typingQueueRef.current = [];
			typingTargetIdRef.current = null;
			// Add to conversation history for context
			conversationHistoryRef.current.push(fullOutput);
		},
		[nodes]
	);

	const handleSend = async () => {
		// Allow sending with just images (no text input required)
		if (
			!activeAgentId ||
			(!input.trim() && uploadedImages.length === 0) ||
			isRunning
		) {
			return;
		}

		const promptText = input.trim() || "Process these images";

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

			const run = await createRun({
				root_agent_id: activeAgentId,
				input: {
					prompt: enhancedPrompt,
					task: promptText,
					conversation_history: conversationHistoryRef.current.slice(-3), // Last 3 exchanges
				},
				images: imageBase64List.length > 0 ? imageBase64List : undefined,
			});

			// Clear images after sending
			setUploadedImages([]);

			// Track accumulated output for final message
			let accumulatedOutput = "";

			// Start SSE streaming
			const eventSource = streamRun(run.id, (event) => {
				if (event.type === "output_chunk") {
					const chunk = event.data || "";
					accumulatedOutput += chunk;
					handleStreamingChunk(event.agent_id || activeAgentId, chunk);
				} else if (event.type === "output") {
					// Final output received
					const finalOutput = event.data || "";
					accumulatedOutput = finalOutput; // Use final output if provided
					handleFinalOutput(
						event.agent_id || activeAgentId,
						finalOutput || accumulatedOutput
					);
				} else if (event.type === "status") {
					if (event.data === "completed") {
						// Ensure we have the final message
						if (accumulatedOutput && currentStreamingMessageIdRef.current) {
							handleFinalOutput(activeAgentId, accumulatedOutput);
						}
						setIsRunning(false);
					}
				} else if (event.type === "error") {
					setError(event.data || "Unknown error");
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
			});

			eventSourceRef.current = eventSource;

			// Handle connection errors
			eventSource.onerror = () => {
				if (eventSource.readyState === EventSource.CLOSED) {
					if (isRunning) {
						setError(
							"Connection closed. The stream finished or was interrupted."
						);
						setIsRunning(false);
						// Finalize message if we have accumulated output
						if (accumulatedOutput && currentStreamingMessageIdRef.current) {
							handleFinalOutput(activeAgentId, accumulatedOutput);
						}
					}
				} else if (eventSource.readyState === EventSource.CONNECTING) {
					console.log("SSE connecting...");
				} else {
					console.error("SSE error occurred");
					if (isRunning && !error) {
						setError(
							"Connection error occurred. Check your network connection."
						);
						setIsRunning(false);
					}
				}
			};
		} catch (err) {
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
			if (typingTimerRef.current !== null) {
				window.clearInterval(typingTimerRef.current);
				typingTimerRef.current = null;
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
								<img
									src={img.preview}
									alt={`Upload ${idx + 1}`}
									className="w-20 h-20 object-cover rounded-lg border border-gray-300"
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
