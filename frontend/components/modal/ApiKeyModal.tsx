"use client";

import { useState } from "react";

interface ApiKeyModalProps {
  isOpen: boolean;
  onSave: (apiKey: string) => void;
}

export function ApiKeyModal({ isOpen, onSave }: ApiKeyModalProps) {
  const [apiKey, setApiKey] = useState(() => {
    if (typeof window !== "undefined") {
      try {
        return localStorage.getItem("GEMINI_API_KEY") || "";
      } catch {
        return "";
      }
    }
    return "";
  });
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const trimmedKey = apiKey.trim();
    if (!trimmedKey) {
      setError("Please enter your Gemini API key");
      return;
    }

    if (trimmedKey.length < 20) {
      setError("API key appears to be invalid (too short)");
      return;
    }

    try {
      localStorage.setItem("GEMINI_API_KEY", trimmedKey);
      onSave(trimmedKey);
    } catch {
      setError("Failed to save API key. Please try again.");
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
      {/* Backdrop - non-dismissible */}
      <div className="absolute inset-0 bg-black bg-opacity-75 backdrop-blur-sm" />

      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-2xl max-w-md w-full z-10 border border-gray-200">
        <div className="p-6">
          <div className="mb-4">
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Gemini API Key Required
            </h3>
            <p className="text-sm text-gray-600">
              To use this application, you need to provide your Google Gemini API key.
              This key is stored locally in your browser and is never sent to our servers.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="api-key-input"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Gemini API Key
              </label>
              <input
                id="api-key-input"
                type="password"
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value);
                  setError("");
                }}
                placeholder="Enter your Gemini API key (AIzaSy...)"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder:text-gray-400"
                autoFocus
              />
              {error && (
                <p className="mt-2 text-sm text-red-600">{error}</p>
              )}
              <p className="mt-2 text-xs text-gray-500">
                Get your API key from{" "}
                <a
                  href="https://aistudio.google.com/app/apikey"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  Google AI Studio
                </a>
              </p>
            </div>

            <div className="flex gap-3 justify-end pt-4">
              <button
                type="submit"
                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Save & Continue
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
