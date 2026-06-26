"use client";

import { useState, useRef, useEffect } from 'react';

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

/**
 * Voice-input WebSocket contract (frontend → backend `/api/audio-stream`)
 * -----------------------------------------------------------------------
 * The backend team (Chaitanya) needs to implement a WebSocket endpoint at
 * `/api/audio-stream` that speaks exactly this protocol:
 *
 *   Client → Server
 *     1. text  : {"event":"start","mimeType":"audio/webm;codecs=opus"}  (sent once, on open)
 *     2. binary: raw audio chunks (the container named in `mimeType`, ~one frame / 250ms)
 *     3. text  : {"event":"stop"}                                       (end-of-stream marker)
 *
 *   Server → Client
 *     - text   : {"event":"transcript","transcript":"<recognised text>"}
 *     - text   : {"event":"done"}                    (optional; server may just close the socket)
 *     - text   : {"event":"error","message":"<reason>"}
 *
 * Concatenating every binary chunk in arrival order reproduces a single valid
 * audio file, so the server can buffer until {"event":"stop"} and transcribe once.
 * Plain-string frames and {"text": "..."} are also accepted for forward-compat.
 */
export default function ChatInput({ onSendMessage, isLoading }: ChatInputProps) {
  const [inputValue, setInputValue] = useState('');
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [micError, setMicError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const socketOpenedRef = useRef(false);
  const transcribeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Tear down the mic, the socket and any pending timer. Safe to call repeatedly.
  const releaseResources = () => {
    if (transcribeTimeoutRef.current) {
      clearTimeout(transcribeTimeoutRef.current);
      transcribeTimeoutRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try { mediaRecorderRef.current.stop(); } catch { /* already stopped */ }
    }
    mediaRecorderRef.current = null;

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    const socket = socketRef.current;
    socketRef.current = null;
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
      try { socket.close(); } catch { /* already closing */ }
    }
  };

  const finishTranscribing = () => {
    setIsRecording(false);
    setIsTranscribing(false);
    releaseResources();
  };

  // Pick the best container/codec the browser can actually record.
  const pickMimeType = (): string => {
    if (typeof MediaRecorder === 'undefined') return '';
    const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
    return candidates.find((type) => MediaRecorder.isTypeSupported(type)) ?? '';
  };

  // http(s)://host  →  ws(s)://host/api/audio-stream  (trailing slashes trimmed).
  const buildWsUrl = (): string => {
    const baseUrl = (process.env.NEXT_PUBLIC_API_URL || 'https://manipal-chatbot.onrender.com').replace(/\/+$/, '');
    return baseUrl.replace(/^http/, 'ws') + '/api/audio-stream';
  };

  const appendTranscript = (text: string) => {
    const clean = (text || '').trim();
    if (!clean) return;
    setInputValue((prev) => {
      const base = prev.trim();
      return base ? `${base} ${clean}` : clean;
    });
  };

  const startRecording = async () => {
    // Ignore double clicks while a session is already connecting/recording.
    if (socketRef.current || isRecording || isTranscribing) return;
    setMicError(null);

    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      setMicError('Microphone access is not supported in this browser.');
      return;
    }
    if (typeof MediaRecorder === 'undefined') {
      setMicError('Audio recording is not supported in this browser.');
      return;
    }

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      console.error('Microphone permission denied:', err);
      setMicError('Microphone permission denied. Please allow mic access and try again.');
      return;
    }
    streamRef.current = stream;

    const mimeType = pickMimeType();
    let socket: WebSocket;
    try {
      socket = new WebSocket(buildWsUrl());
    } catch (err) {
      console.error('Failed to open voice WebSocket:', err);
      setMicError('Could not connect to the voice service.');
      releaseResources();
      return;
    }
    socketOpenedRef.current = false;
    socketRef.current = socket;

    socket.onopen = () => {
      socketOpenedRef.current = true;

      // Announce the codec so the server can label the buffer correctly.
      try { socket.send(JSON.stringify({ event: 'start', mimeType })); } catch { /* noop */ }

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0 && socket.readyState === WebSocket.OPEN) {
          socket.send(event.data);
        }
      };

      // stop() flushes the final chunk to ondataavailable first, *then* fires
      // onstop — so by here the server has every byte and we can signal the end.
      recorder.onstop = () => {
        if (socket.readyState === WebSocket.OPEN) {
          try { socket.send(JSON.stringify({ event: 'stop' })); } catch { /* noop */ }
        }
      };

      recorder.start(250); // emit a chunk roughly every 250ms
      setIsRecording(true);
    };

    socket.onmessage = (event) => {
      if (typeof event.data !== 'string') return; // we only expect text frames back
      try {
        const data = JSON.parse(event.data);
        if (data.event === 'error') {
          setMicError(typeof data.message === 'string' ? data.message : 'Transcription failed.');
          finishTranscribing();
          return;
        }
        const text = data.transcript ?? data.text;
        if (typeof text === 'string') appendTranscript(text);
        if (data.event === 'done') finishTranscribing();
      } catch {
        appendTranscript(event.data); // tolerate a plain-string transcript
      }
    };

    socket.onerror = (err) => {
      console.error('Voice WebSocket error:', err);
    };

    socket.onclose = () => {
      // If the socket never opened, the endpoint is unreachable — surface that.
      if (!socketOpenedRef.current) {
        setMicError('Could not reach the voice service. Please try again later.');
      }
      finishTranscribing();
    };
  };

  const stopRecording = () => {
    if (!isRecording) return;

    // Hand off to the "transcribing" phase; the transcript arrives over the socket.
    setIsRecording(false);
    setIsTranscribing(true);

    // Stopping the recorder flushes the last chunk and triggers onstop, which
    // sends the {event:'stop'} marker. We keep the socket open to receive the
    // transcript — releaseResources() closes it once we're done.
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try { mediaRecorderRef.current.stop(); } catch { /* already stopped */ }
    }

    // Release the mic right away; we don't need it during transcription.
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    // Safety net so the UI never hangs if the server goes silent.
    transcribeTimeoutRef.current = setTimeout(() => {
      setMicError((prev) => prev ?? 'The voice service did not respond in time.');
      finishTranscribing();
    }, 15000);
  };

  // Release everything if the component unmounts mid-recording.
  useEffect(() => releaseResources, []);

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
            disabled={isLoading || isRecording || isTranscribing}
            placeholder={
              isRecording
                ? 'Listening... Speak now'
                : isTranscribing
                ? 'Transcribing...'
                : activeTool
                ? `${tools.find(t => t.id === activeTool)?.label} mode — ask anything...`
                : 'Ask anything about Manipal...'
            }
            className={`flex-1 text-sm text-gray-700 bg-transparent focus:outline-none placeholder-gray-300 py-1.5 disabled:opacity-50 ${
              isRecording ? 'text-red-500 font-medium animate-pulse' : ''
            }`}
          />

          {/* Voice Button */}
          <button
            type="button"
            disabled={isLoading || isTranscribing}
            onClick={isRecording ? stopRecording : startRecording}
            className={`p-1.5 rounded-lg transition-all relative ${
              isRecording
                ? 'bg-red-500 text-white hover:bg-red-600 animate-pulse cursor-pointer'
                : isTranscribing
                ? 'text-manipal-orange cursor-wait'
                : 'text-gray-400 hover:text-manipal-orange hover:bg-orange-50 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed'
            }`}
            title={
              isRecording
                ? 'Stop recording'
                : isTranscribing
                ? 'Transcribing…'
                : 'Start voice input'
            }
          >
            {isTranscribing ? (
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={4} />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : isRecording ? (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10h6v4H9z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            )}
            {isRecording && (
              <span className="absolute inset-0 rounded-lg bg-red-500 opacity-75 animate-ping -z-10" />
            )}
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
      {micError ? (
        <p className="text-center text-[10px] text-red-400 mt-2" role="alert">
          {micError}
        </p>
      ) : (
        <p className="text-center text-[10px] text-gray-300 mt-2">
          Campus AI can make mistakes. Verify important information.
        </p>
      )}
    </div>
  );
}