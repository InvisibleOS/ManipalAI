"use client";

import { useChat } from '@/context/ChatContext';

/**
 * Distinct, always-visible entry point for the exclusive "Interview Mode" —
 * a Gemini-Live–style voice-to-voice experience (separate from the text chat).
 * Lives in the global header.
 */
export default function InterviewModeButton() {
  const { openInterview } = useChat();

  return (
    <button
      type="button"
      onClick={openInterview}
      title="Start a live voice interview"
      className="group flex items-center gap-2 rounded-full bg-white text-manipal-orange pl-2.5 pr-3.5 py-1.5 text-xs font-semibold shadow-sm hover:shadow-md hover:bg-orange-50 transition-all cursor-pointer"
    >
      <span className="relative flex items-center justify-center">
        <span className="absolute w-2 h-2 rounded-full bg-red-500 opacity-75 animate-ping" />
        <span className="relative w-2 h-2 rounded-full bg-red-500" />
      </span>
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
      </svg>
      Interview Mode
    </button>
  );
}
