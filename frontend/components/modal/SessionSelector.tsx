"use client";

import { useState, useEffect } from "react";
import { listSessions, createSession, deleteSession, Session } from "@/lib/api";
import { ConfirmModal } from "./ConfirmModal";

interface SessionSelectorProps {
	isOpen: boolean;
	onSelect: (sessionId: string | null) => void;
}

export function SessionSelector({ isOpen, onSelect }: SessionSelectorProps) {
	const [sessions, setSessions] = useState<Session[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [newSessionName, setNewSessionName] = useState("");
	const [isCreating, setIsCreating] = useState(false);
	const [sessionToDelete, setSessionToDelete] = useState<Session | null>(null);
	const [isDeleting, setIsDeleting] = useState(false);

	useEffect(() => {
		if (isOpen) {
			loadSessions();
		}
	}, [isOpen]);

	const loadSessions = async () => {
		setIsLoading(true);
		setError(null);
		try {
			const data = await listSessions();
			setSessions(data);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to load sessions");
		} finally {
			setIsLoading(false);
		}
	};

	const handleCreateSession = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!newSessionName.trim()) {
			setError("Session name cannot be empty");
			return;
		}

		setIsCreating(true);
		setError(null);
		try {
			const session = await createSession({ name: newSessionName.trim() });
			localStorage.setItem("SESSION_ID", session.id);
			onSelect(session.id);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to create session");
		} finally {
			setIsCreating(false);
		}
	};

	const handleSelectSession = (sessionId: string) => {
		localStorage.setItem("SESSION_ID", sessionId);
		onSelect(sessionId);
	};

	const handleDeleteClick = (e: React.MouseEvent, session: Session) => {
		e.stopPropagation(); // Prevent session selection when clicking delete
		setSessionToDelete(session);
	};

	const handleConfirmDelete = async () => {
		if (!sessionToDelete) return;

		setIsDeleting(true);
		setError(null);
		try {
			await deleteSession(sessionToDelete.id);
			
			// If deleted session is the current one, clear it
			const currentSessionId = localStorage.getItem("SESSION_ID");
			if (currentSessionId === sessionToDelete.id) {
				localStorage.removeItem("SESSION_ID");
				onSelect(null); // Trigger re-evaluation
			}
			
			// Reload sessions list
			await loadSessions();
			setSessionToDelete(null);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to delete session");
			setIsDeleting(false);
		} finally {
			setIsDeleting(false);
		}
	};

	const handleCancelDelete = () => {
		setSessionToDelete(null);
	};

	if (!isOpen) return null;

	return (
		<>
			{/* Delete Confirmation Modal */}
			<ConfirmModal
				isOpen={!!sessionToDelete}
				title="Delete Session"
				message={`Are you sure you want to delete "${sessionToDelete?.name}"?\n\nThis will permanently delete all agents, links, and runs associated with this session. This action cannot be undone.`}
				confirmText="Delete"
				cancelText="Cancel"
				onConfirm={handleConfirmDelete}
				onCancel={handleCancelDelete}
				variant="danger"
			/>

			<div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
				<div className="absolute inset-0 bg-black bg-opacity-75 backdrop-blur-sm" />
				<div className="relative bg-white rounded-xl shadow-2xl max-w-2xl w-full z-10 border border-gray-200 max-h-[80vh] flex flex-col">
				<div className="p-6 border-b border-gray-200">
					<h3 className="text-xl font-semibold text-gray-900 mb-2">
						Select or Create Session
					</h3>
					<p className="text-sm text-gray-600">
						Each session has its own isolated agent ecosystem. Choose an existing session or create a new one.
					</p>
				</div>

				<div className="flex-1 overflow-y-auto p-6 space-y-4">
					{error && (
						<div className="bg-red-50 border border-red-200 rounded-lg p-3">
							<p className="text-red-800 text-sm">{error}</p>
						</div>
					)}

					{/* Create New Session */}
					<div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
						<h4 className="text-sm font-semibold text-gray-900 mb-3">
							Create New Session
						</h4>
						<form onSubmit={handleCreateSession} className="flex gap-2">
							<input
								type="text"
								value={newSessionName}
								onChange={(e) => {
									setNewSessionName(e.target.value);
									setError(null);
								}}
								placeholder="Enter session name..."
								className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm text-gray-900"
								disabled={isCreating}
							/>
							<button
								type="submit"
								disabled={isCreating || !newSessionName.trim()}
								className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors">
								{isCreating ? "Creating..." : "Create"}
							</button>
						</form>
					</div>

					{/* Existing Sessions */}
					<div>
						<h4 className="text-sm font-semibold text-gray-900 mb-3">
							Existing Sessions
						</h4>
						{isLoading ? (
							<div className="text-center py-8 text-gray-500 text-sm">
								Loading sessions...
							</div>
						) : sessions.length === 0 ? (
							<div className="text-center py-8 text-gray-500 text-sm">
								No sessions found. Create a new one above.
							</div>
						) : (
							<div className="space-y-2">
								{sessions.map((session) => (
									<div
										key={session.id}
										className="w-full p-4 border border-gray-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 transition-colors">
										<div className="flex items-center justify-between gap-4">
											<button
												onClick={() => handleSelectSession(session.id)}
												className="flex-1 text-left hover:opacity-80 transition-opacity">
												<div className="font-medium text-gray-900">
													{session.name}
												</div>
												<div className="text-xs text-gray-500 mt-1">
													Created: {new Date(session.created_at).toLocaleString()}
												</div>
												<div className="text-xs text-gray-500">
													Last accessed: {new Date(session.last_accessed).toLocaleString()}
												</div>
											</button>
											<div className="flex items-center gap-2 ml-4 flex-shrink-0">
												<button
													onClick={(e) => handleDeleteClick(e, session)}
													disabled={isDeleting}
													className="px-3 py-1.5 text-red-600 hover:text-red-700 hover:bg-red-50 border border-red-300 hover:border-red-400 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
													title="Delete session">
													Delete
												</button>
												<button
													onClick={() => handleSelectSession(session.id)}
													className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white border border-blue-700 hover:border-blue-800 rounded-lg text-sm font-medium transition-colors">
													Select →
												</button>
											</div>
										</div>
									</div>
								))}
							</div>
						)}
					</div>
				</div>
			</div>
		</div>
		</>
	);
}
