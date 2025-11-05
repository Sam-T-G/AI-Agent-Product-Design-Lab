"use client";

import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export interface ChatMessage {
	id: string;
	type: "user" | "agent" | "internal";
	agentId?: string;
	agentName?: string;
	content: string;
	timestamp: Date;
}

interface AgentChatProps {
	messages: ChatMessage[];
	showInternal: boolean;
	rootAgentId?: string;
	nodes: Array<{ id: string; data: { agent: { name: string } } }>;
}

export function AgentChat({
	messages,
	showInternal,
	rootAgentId,
	nodes,
}: AgentChatProps) {
	const pastelFromId = (id: string | undefined) => {
		const key = id || "unknown";
		let hash = 0;
		for (let i = 0; i < key.length; i++)
			hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
		const hue = hash % 360;
		return {
			bg: `hsl(${hue} 100% 95%)`,
			text: `hsl(${hue} 40% 25%)`,
			border: `hsl(${hue} 70% 70%)`,
		};
	};
	// Filter messages based on toggle
	const visibleMessages = useMemo(() => {
		if (showInternal) {
			return messages;
		}
		// Only show user messages and root agent messages
		return messages.filter(
			(msg) =>
				msg.type === "user" ||
				(msg.type === "agent" && msg.agentId === rootAgentId)
		);
	}, [messages, showInternal, rootAgentId]);

	const getAgentName = (agentId?: string) => {
		if (!agentId) return "Unknown Agent";
		const node = nodes.find((n) => n.id === agentId);
		return node?.data.agent.name || "Unknown Agent";
	};

	return (
		<div className="p-3 sm:p-4 space-y-3 sm:space-y-4 min-h-full">
			{visibleMessages.length === 0 ? (
				<div className="flex items-center justify-center min-h-[200px] text-gray-500 text-sm">
					<p>Start a conversation with your agent...</p>
				</div>
			) : (
				visibleMessages.map((message) => {
					const isUser = message.type === "user";
					const isInternal = message.type === "internal";
					const agentName = message.agentName || getAgentName(message.agentId);

					const colors =
						!isUser && !isInternal ? pastelFromId(message.agentId) : undefined;
					return (
						<div
							key={message.id}
							className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
							<div
								className={`max-w-[80%] rounded-2xl px-4 py-3 ${
									isUser
										? "bg-blue-600 text-white"
										: isInternal
										? "bg-amber-50 border border-amber-200 text-amber-900"
										: "text-gray-900"
								}`}
								style={
									!isUser && !isInternal
										? {
												background: colors?.bg,
												border: `1px solid ${colors?.border}`,
												color: colors?.text,
										  }
										: undefined
								}>
								{/* Agent name header for non-user messages */}
								{!isUser && (
									<div
										className={`text-xs font-semibold mb-1 ${
											isInternal ? "text-amber-700" : "text-gray-600"
										}`}>
										{isInternal ? "🔗 Internal: " : ""}
										{agentName}
									</div>
								)}

								{/* Message content with markdown */}
								<div
									className={`prose prose-sm max-w-none ${
										isUser
											? "prose-invert prose-headings:text-white prose-p:text-white prose-strong:text-white prose-code:text-blue-100"
											: isInternal
											? "prose-amber prose-headings:text-amber-900 prose-p:text-amber-900 prose-strong:text-amber-900"
											: "prose-gray prose-headings:text-gray-900 prose-p:text-gray-900"
									}`}>
									<ReactMarkdown remarkPlugins={[remarkGfm]}>
										{message.content}
									</ReactMarkdown>
								</div>

								{/* Timestamp */}
								<div
									className={`text-xs mt-2 ${
										isUser
											? "text-blue-100"
											: isInternal
											? "text-amber-600"
											: "text-gray-500"
									}`}>
									{message.timestamp.toLocaleTimeString([], {
										hour: "2-digit",
										minute: "2-digit",
									})}
								</div>
							</div>
						</div>
					);
				})
			)}
		</div>
	);
}
