"use client";
import { useState } from 'react';

export default function Sidebar() {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <aside
      className={`bg-white h-full border-r border-gray-100 flex flex-col transition-all duration-300 ease-in-out relative z-20 ${isOpen ? 'w-56' : 'w-16'}`}
    >
      {/* Collapse toggle */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="absolute -right-3 top-1/2 -translate-y-1/2 bg-white border border-gray-200 rounded-full p-1 text-gray-400 hover:text-manipal-orange z-30 shadow-sm transition-colors"
      >
        <svg
          className={`w-3.5 h-3.5 transition-transform ${isOpen ? '' : 'rotate-180'}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      {/* New Chat - Pinned to the top */}
      <div className="p-3">
        {isOpen ? (
          <button className="w-full bg-orange-50 hover:bg-orange-100 text-manipal-orange font-medium py-2 px-3 rounded-full flex items-center justify-center gap-2 transition-colors text-sm border border-orange-100">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
            </svg>
            New Chat
          </button>
        ) : (
          <button className="w-9 h-9 mx-auto bg-orange-50 hover:bg-orange-100 text-manipal-orange rounded-xl flex items-center justify-center transition-colors border border-orange-100">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
            </svg>
          </button>
        )}
      </div>
    </aside>
  );
}