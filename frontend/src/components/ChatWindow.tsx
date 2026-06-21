"use client";
import { useState, useRef, useEffect, FormEvent } from "react";
import { streamChat } from "../lib/sse";
import { request } from "../lib/api";
import { logout } from "../lib/auth";
import MessageBubble from "./MessageBubble";
import SessionSidebar from "./SessionSidebar";
import type { Message, SessionEntry, SessionHistoryResponse } from "../types";

const SESSIONS_KEY = "session_ids";

function loadSessions(): SessionEntry[] {
  try {
    return JSON.parse(localStorage.getItem(SESSIONS_KEY) ?? "[]") as SessionEntry[];
  } catch {
    return [];
  }
}

function saveSessions(sessions: SessionEntry[]): void {
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
}

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamBuffer, setStreamBuffer] = useState("");
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<SessionEntry[]>([]);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setSessions(loadSessions());
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamBuffer]);

  async function loadSession(uuid: string) {
    setError("");
    try {
      const data = await request<SessionHistoryResponse>(
        `/api/v1/chat/${uuid}`,
      );
      setMessages(data.messages);
      setActiveSessionId(uuid);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load session");
    }
  }

  function handleNewChat() {
    setActiveSessionId(null);
    setMessages([]);
    setStreamBuffer("");
    setError("");
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || streaming) return;

    const userMsg: Message = {
      id: Date.now(),
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStreaming(true);
    setStreamBuffer("");
    setError("");

    let accumulated = "";
    let newSessionId: string | null = null;

    try {
      await streamChat(
        text,
        activeSessionId,
        (chunk) => {
          accumulated += chunk;
          setStreamBuffer(accumulated);
        },
        (uuid) => {
          newSessionId = uuid;
        },
      );

      const assistantMsg: Message = {
        id: Date.now() + 1,
        role: "assistant",
        content: accumulated,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setStreamBuffer("");

      if (newSessionId) {
        setActiveSessionId(newSessionId);
        const entry: SessionEntry = {
          uuid: newSessionId,
          preview: text.slice(0, 40),
          created_at: new Date().toISOString(),
        };
        const updated = [entry, ...loadSessions().filter((s) => s.uuid !== newSessionId)];
        saveSessions(updated);
        setSessions(updated);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Stream failed");
      setStreamBuffer("");
    } finally {
      setStreaming(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as FormEvent);
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-10 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div
        className={`fixed md:static z-20 h-full transition-transform duration-200 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        } md:translate-x-0`}
      >
        <SessionSidebar
          sessions={sessions}
          activeUuid={activeSessionId}
          onSelect={(uuid) => {
            loadSession(uuid);
            setSidebarOpen(false);
          }}
          onNewChat={() => {
            handleNewChat();
            setSidebarOpen(false);
          }}
          onLogout={logout}
        />
      </div>

      {/* Main */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header (mobile) */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-gray-800">
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-gray-400 hover:text-white"
            aria-label="Open sidebar"
          >
            ☰
          </button>
          <span className="font-semibold text-sm">FIFA 2026 Analyst</span>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          {messages.length === 0 && !streaming && (
            <div className="text-center text-gray-500 mt-20 text-sm">
              Ask anything about FIFA 2026
            </div>
          )}
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
          {streamBuffer && (
            <div className="flex justify-start mb-3">
              <div className="max-w-[80%] px-4 py-2 rounded-2xl rounded-bl-sm text-sm bg-gray-800 text-gray-100 whitespace-pre-wrap">
                {streamBuffer}
                <span className="animate-pulse">▋</span>
              </div>
            </div>
          )}
          {error && (
            <p role="alert" className="text-red-400 text-sm text-center my-2">
              {error}
            </p>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <form
          onSubmit={handleSubmit}
          className="p-4 border-t border-gray-800 flex gap-2"
        >
          <textarea
            ref={inputRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message FIFA 2026 Analyst…"
            disabled={streaming}
            className="flex-1 resize-none bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 text-sm focus:outline-none focus:border-blue-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={streaming || !input.trim()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 rounded-xl text-sm font-semibold"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
