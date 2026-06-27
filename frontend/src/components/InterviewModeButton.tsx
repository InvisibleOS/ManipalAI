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
      className="text-xs text-white border border-white/30 hover:border-white/50 hover:bg-white/10 rounded px-3 py-1.5 font-medium transition-all cursor-pointer"
    >
      Interview Mode
    </button>
  );
}
