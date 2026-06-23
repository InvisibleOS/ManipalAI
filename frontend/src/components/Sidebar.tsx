"use client";

import { useState } from 'react';
import { useChat } from '@/context/ChatContext';

export default function Sidebar() {
  const [isOpen, setIsOpen] = useState(true);
  const { sessions, activeSessionId, createSession, deleteSession, setActiveSessionId } = useChat();

  return (
    <aside
      className={`bg-white h-full border-r border-gray-100 flex flex-col transition-all duration-300 ease-in-out relative z-20 ${
        isOpen ? 'w-56' : 'w-16'
      }`}
    >
      {/* Collapse toggle */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="absolute -right-3 top-1/2 -translate-y-1/2 bg-white border border-gray-200 rounded-full p-1 text-gray-400 hover:text-manipal-orange z-30 shadow-sm transition-colors cursor-pointer"
        title={isOpen ? "Collapse Sidebar" : "Expand Sidebar"}
      >
        <svg
          className={`w-3.5 h-3.5 transition-transform ${isOpen ? '' : 'rotate-180'}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      {/* New Chat Button */}
      <div className="p-3 shrink-0">
        {isOpen ? (
          <button
            onClick={() => createSession()}
            className="w-full bg-orange-50 hover:bg-orange-100 text-manipal-orange font-medium py-2 px-3 rounded-full flex items-center justify-center gap-2 transition-colors text-sm border border-orange-100 cursor-pointer"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
            </svg>
            New Chat
          </button>
        ) : (
          <button
            onClick={() => createSession()}
            className="w-9 h-9 mx-auto bg-orange-50 hover:bg-orange-100 text-manipal-orange rounded-xl flex items-center justify-center transition-colors border border-orange-100 cursor-pointer"
            title="New Chat"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
            </svg>
          </button>
        )}
      </div>

      {/* Chat History List */}
      <div className="flex-1 overflow-y-auto px-2 py-1 space-y-1">
        {isOpen && (
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider px-3 mb-2 shrink-0">
            Recent Chats
          </p>
        )}

        {sessions.map((session) => {
          const isActive = session.id === activeSessionId;
          return (
            <div
              key={session.id}
              onClick={() => setActiveSessionId(session.id)}
              className={`group flex items-center justify-between px-3 py-2 rounded-xl text-xs transition-all cursor-pointer ${
                isActive
                  ? 'bg-orange-50/60 text-manipal-orange font-medium border-l-2 border-manipal-orange'
                  : 'text-gray-600 hover:bg-slate-50 hover:text-gray-900'
              }`}
            >
              <div className="flex items-center gap-2 overflow-hidden w-full">
                {/* Chat icon */}
                <svg
                  className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-manipal-orange' : 'text-gray-400'}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
                {isOpen && (
                  <span className="truncate pr-1 text-left w-full select-none">
                    {session.title || 'New Chat'}
                  </span>
                )}
              </div>

              {/* Delete chat button (only shown when expanded & hovered, or if active) */}
              {isOpen && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteSession(session.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 hover:text-red-500 text-gray-400 p-0.5 rounded transition-all cursor-pointer shrink-0"
                  title="Delete Chat"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              )}
            </div>
          );
        })}
      </div>
    </aside>
  );
}