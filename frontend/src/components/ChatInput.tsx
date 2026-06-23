"use client";

import { useState } from 'react';

const tools = [
  {
    id: 'resume',
    label: 'Resume Scanner',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
  {
    id: 'interview',
    label: 'Interview Mode',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
      </svg>
    ),
  },
  {
    id: 'placement',
    label: 'Placement Q&A',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ),
  },
  {
    id: 'study',
    label: 'Study Aid',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
      </svg>
    ),
  },
];

interface ChatInputProps {
  onSendMessage: (text: string, activeTool: string | null) => void;
  isLoading: boolean;
}

export default function ChatInput({ onSendMessage, isLoading }: ChatInputProps) {
  const [inputValue, setInputValue] = useState('');
  const [activeTool, setActiveTool] = useState<string | null>(null);

  const handleToolClick = (id: string) => {
    setActiveTool(prev => (prev === id ? null : id));
  };

  const handleSend = () => {
    if (inputValue.trim() && !isLoading) {
      onSendMessage(inputValue, activeTool);
      setInputValue('');
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto shrink-0">
      <div
        className="bg-white rounded-2xl border border-gray-200 overflow-hidden transition-all"
        style={{
          boxShadow: '0 2px 16px rgba(243,112,33,0.07), 0 1px 4px rgba(0,0,0,0.05)',
        }}
      >
        {/* Text input row */}
        <div className="flex items-center px-4 pt-3 pb-2 gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleSend();
              }
            }}
            disabled={isLoading}
            placeholder={
              activeTool
                ? `${tools.find(t => t.id === activeTool)?.label} mode — ask anything...`
                : 'Ask anything about Manipal...'
            }
            className="flex-1 text-sm text-gray-700 bg-transparent focus:outline-none placeholder-gray-300 py-1.5 disabled:opacity-50"
          />

          {/* Voice Button */}
          <button
            type="button"
            disabled={isLoading}
            className="p-1.5 rounded-lg text-gray-400 hover:text-manipal-orange hover:bg-orange-50 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </button>

          {/* Send Button */}
          <button
            type="button"
            onClick={handleSend}
            disabled={!inputValue.trim() || isLoading}
            className={`p-1.5 rounded-lg transition-all cursor-pointer ${
              inputValue.trim() && !isLoading
                ? 'bg-manipal-orange text-white shadow-sm hover:bg-orange-600'
                : 'text-gray-300 cursor-default disabled:opacity-50 disabled:cursor-not-allowed'
            }`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        {/* Tool chips row — Gemini-style */}
        <div className="flex items-center gap-1.5 px-3 pb-3 pt-0.5">
          {tools.map((tool) => (
            <button
              key={tool.id}
              type="button"
              disabled={isLoading}
              onClick={() => handleToolClick(tool.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
                activeTool === tool.id
                  ? 'bg-orange-50 border-orange-200 text-manipal-orange'
                  : 'bg-gray-50 border-gray-200 text-gray-500 hover:border-orange-200 hover:text-manipal-orange hover:bg-orange-50'
              }`}
            >
              {tool.icon}
              {tool.label}
            </button>
          ))}
        </div>
      </div>
      <p className="text-center text-[10px] text-gray-300 mt-2">
        Campus AI can make mistakes. Verify important information.
      </p>
    </div>
  );
}