"use client";
import type { SessionEntry } from "../types";

interface Props {
  sessions: SessionEntry[];
  activeUuid: string | null;
  onSelect: (uuid: string) => void;
  onNewChat: () => void;
  onLogout: () => void;
}

export default function SessionSidebar({
  sessions,
  activeUuid,
  onSelect,
  onNewChat,
  onLogout,
}: Props) {
  return (
    <aside className="flex flex-col h-full w-64 min-w-[16rem] bg-gray-900 border-r border-gray-800">
      <div className="p-3 border-b border-gray-800">
        <button
          onClick={onNewChat}
          className="w-full py-2 rounded bg-blue-600 hover:bg-blue-700 text-sm font-semibold"
        >
          + New chat
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto p-2 flex flex-col gap-1">
        {sessions.length === 0 && (
          <p className="text-xs text-gray-500 text-center mt-4">
            No sessions yet
          </p>
        )}
        {sessions.map((s) => (
          <button
            key={s.uuid}
            onClick={() => onSelect(s.uuid)}
            className={`w-full text-left px-3 py-2 rounded text-sm truncate ${
              s.uuid === activeUuid
                ? "bg-gray-700 text-white"
                : "text-gray-300 hover:bg-gray-800"
            }`}
          >
            {s.preview || "Chat session"}
          </button>
        ))}
      </nav>

      <div className="p-3 border-t border-gray-800">
        <button
          onClick={onLogout}
          className="w-full py-2 rounded bg-gray-800 hover:bg-gray-700 text-sm text-gray-300"
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}
