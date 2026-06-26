"use client";

import { useChat } from '@/context/ChatContext';
import InterviewLive from '@/components/InterviewLive';

/**
 * Mounts the immersive Interview Mode overlay once, globally, wired to the
 * shared open-state in ChatContext so it can be launched from anywhere
 * (e.g. the header's Interview Mode button).
 */
export default function InterviewLiveHost() {
  const { isInterviewOpen, closeInterview } = useChat();
  return <InterviewLive open={isInterviewOpen} onClose={closeInterview} />;
}
