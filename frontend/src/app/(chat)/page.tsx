"use client";

import { useRef, useEffect } from 'react';
import ChatInput from '@/components/ChatInput';
import { useChat } from '@/context/ChatContext';

export default function Home() {
  const { activeSession, isLoading, sendMessage } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const messages = activeSession?.messages || [];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSendMessage = (text: string, activeTool: string | null) => {
    sendMessage(text, activeTool);
  };

  // Helper function to format bot text, supporting bold (**text**) and line breaks
  const formatText = (text: string) => {
    return text.split('\n').map((line, i) => {
      // Bold regex mapping
      const parts = line.split(/(\*\*.*?\*\*)/g);
      const content = parts.map((part, j) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return (
            <strong key={j} className="font-semibold text-slate-800">
              {part.slice(2, -2)}
            </strong>
          );
        }
        return part;
      });

      return (
        <p key={i} className="text-sm leading-relaxed mb-1 text-slate-700">
          {content}
        </p>
      );
    });
  };

  return (
    <main className="flex-1 relative flex flex-col h-full bg-slate-50/50 overflow-hidden">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-6 flex flex-col">
        {messages.length === 0 ? (
          /* Welcome View */
          <div className="flex-1 flex flex-col items-center justify-center max-w-xl mx-auto z-10 relative">
            <h1
              className="text-4xl font-light text-slate-800 mb-3 text-center"
              style={{ letterSpacing: '-0.03em' }}
            >
              Welcome to <span className="font-semibold text-manipal-orange">Campus AI</span>
            </h1>
            <p className="text-sm text-slate-400 font-normal mb-8 text-center">
              Your intelligent guide for MIT Bengaluru. Ask about placements, resumes, calendar, and schedule.
            </p>

            <div className="flex flex-wrap justify-center gap-2.5">
              {[
                'Help with Resume ATS',
                'Practice Behavioral Interview',
                'Company question bank',
                'Upcoming placements',
                'Check my schedule',
              ].map((label) => (
                <button
                  key={label}
                  type="button"
                  onClick={() => handleSendMessage(label, activeSession?.activeTool || null)}
                  className="px-4 py-2 bg-white border border-slate-200 rounded-full text-xs text-slate-600 shadow-sm hover:shadow-md hover:border-orange-200 hover:text-manipal-orange transition-all cursor-pointer"
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Chat Message History */
          <div className="max-w-3xl w-full mx-auto space-y-4 flex flex-col pb-4">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex flex-col max-w-[80%] ${
                  m.sender === 'user' ? 'self-end items-end' : 'self-start items-start'
                }`}
              >
                {/* Sender label */}
                <div className="flex items-center gap-1.5 mb-1 px-1">
                  <span className="text-[10px] text-slate-400 font-semibold">
                    {m.sender === 'user' ? 'You' : 'Campus AI'}
                  </span>
                  <span className="text-[9px] text-slate-300">
                    {new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>

                {/* Message bubble */}
                <div
                  className={`px-4 py-3 rounded-2xl shadow-sm ${
                    m.sender === 'user'
                      ? 'bg-manipal-orange text-white rounded-tr-none'
                      : m.isError
                      ? 'bg-red-50 border border-red-200 text-red-800 rounded-tl-none'
                      : 'bg-white border border-slate-100 text-slate-800 rounded-tl-none'
                  }`}
                >
                  {m.sender === 'user' ? (
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{m.text}</p>
                  ) : (
                    <div className="space-y-1.5">{formatText(m.text)}</div>
                  )}
                </div>
              </div>
            ))}

            {/* Bouncing Typing Indicator */}
            {isLoading && (
              <div className="flex flex-col self-start items-start max-w-[80%]">
                <div className="flex items-center gap-1.5 mb-1 px-1">
                  <span className="text-[10px] text-slate-400 font-semibold">Campus AI</span>
                </div>
                <div className="bg-white border border-slate-100 px-4 py-3.5 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 bg-manipal-orange rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 bg-manipal-orange rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 bg-manipal-orange rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="p-5 pb-8 w-full z-10 relative flex justify-center border-t border-slate-100/50 bg-white">
        <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
      </div>
    </main>
  );
}