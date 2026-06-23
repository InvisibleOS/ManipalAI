"use client";

import React, { createContext, useContext, useState, useEffect } from 'react';

export interface Message {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  timestamp: string;
  isError?: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  activeTool: string | null;
  createdAt: string;
}

interface ChatContextType {
  sessions: ChatSession[];
  activeSessionId: string | null;
  isLoading: boolean;
  createSession: () => string;
  deleteSession: (id: string) => void;
  sendMessage: (text: string, activeTool: string | null) => Promise<void>;
  setActiveSessionId: (id: string | null) => void;
  activeSession: ChatSession | null;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load sessions from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem('manipal_chat_sessions');
      if (stored) {
        const parsed = JSON.parse(stored) as ChatSession[];
        setSessions(parsed);
        if (parsed.length > 0) {
          setActiveSessionId(parsed[0].id);
        }
      } else {
        // Create an initial session if none exist
        const initialSession: ChatSession = {
          id: 'initial-session-id',
          title: 'New Chat',
          messages: [],
          activeTool: null,
          createdAt: new Date().toISOString()
        };
        setSessions([initialSession]);
        setActiveSessionId(initialSession.id);
      }
    } catch (e) {
      console.error('Failed to load chat sessions:', e);
    }
    setIsLoaded(true);
  }, []);

  // Save sessions to localStorage when they change
  useEffect(() => {
    if (isLoaded) {
      try {
        localStorage.setItem('manipal_chat_sessions', JSON.stringify(sessions));
      } catch (e) {
        console.error('Failed to save chat sessions:', e);
      }
    }
  }, [sessions, isLoaded]);

  const activeSession = sessions.find(s => s.id === activeSessionId) || null;

  const createSession = () => {
    const newId = Math.random().toString(36).substring(2, 11);
    const newSession: ChatSession = {
      id: newId,
      title: 'New Chat',
      messages: [],
      activeTool: null,
      createdAt: new Date().toISOString()
    };
    setSessions(prev => [newSession, ...prev]);
    setActiveSessionId(newId);
    return newId;
  };

  const deleteSession = (id: string) => {
    setSessions(prev => {
      const filtered = prev.filter(s => s.id !== id);
      // If we deleted the active session, switch to another one
      if (activeSessionId === id) {
        if (filtered.length > 0) {
          setActiveSessionId(filtered[0].id);
        } else {
          // If no sessions remain, create a new one
          const newSession: ChatSession = {
            id: 'fallback-session-id',
            title: 'New Chat',
            messages: [],
            activeTool: null,
            createdAt: new Date().toISOString()
          };
          setActiveSessionId(newSession.id);
          return [newSession];
        }
      }
      return filtered;
    });
  };

  const sendMessage = async (text: string, activeTool: string | null) => {
    if (!activeSessionId) return;

    const userMessage: Message = {
      id: Math.random().toString(36).substring(2, 11),
      sender: 'user',
      text,
      timestamp: new Date().toISOString()
    };

    // Update session messages and set tool
    setSessions(prev => prev.map(s => {
      if (s.id === activeSessionId) {
        const isFirstMessage = s.messages.length === 0;
        const newTitle = isFirstMessage 
          ? (text.length > 25 ? text.substring(0, 25) + '...' : text) 
          : s.title;

        return {
          ...s,
          title: newTitle,
          activeTool,
          messages: [...s.messages, userMessage]
        };
      }
      return s;
    }));

    setIsLoading(true);

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://manipal-chatbot.onrender.com';
      const response = await fetch(`${baseUrl}/mock/ai-chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: text,
          tool: activeTool
        })
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const resJson = await response.json();
      let aiText = '';

      if (resJson && typeof resJson === 'object') {
        const rootData = resJson.data || resJson;
        aiText = rootData.message || rootData.response || rootData.text || JSON.stringify(resJson);
      } else {
        aiText = String(resJson);
      }

      // If placeholder response is returned, customize it to make the experience wower!
      if (aiText === 'Placeholder.') {
        if (activeTool === 'resume') {
          aiText = "📄 **Resume Scanner Loaded**\n\nI've analyzed your request for Resume feedback. Please paste your resume text here, or ask about ATS optimization tips. Generally, for MIT placement drives, ensure:\n- You use clear action verbs (e.g. *Developed*, *Led*, *Optimized*)\n- Quantify results (e.g. *Improved speed by 35%*)\n- Keep format strictly single-page.";
        } else if (activeTool === 'interview') {
          aiText = "🎙️ **Interview Mode Activated**\n\nLet's practice your behavioral interview skills. Please answer the following question:\n\n*\"Can you describe a challenging technical project you worked on and how you resolved the obstacles?\"*";
        } else if (activeTool === 'placement') {
          aiText = "💼 **Placement Q&A Hub**\n\nI'm ready to answer placement queries. You can ask about:\n- Past packages at MIT B.Tech CSE/ECE/etc.\n- Dynamic syllabus or interview rounds for JP Morgan, Goldman Sachs, etc.\n- Recruitment schedule updates.";
        } else {
          aiText = `Hello! I am your MIT Campus Assistant. You asked: "${text}". How else can I assist you with placements, studies, or schedules today?`;
        }
      }

      const aiMessage: Message = {
        id: Math.random().toString(36).substring(2, 11),
        sender: 'ai',
        text: aiText,
        timestamp: new Date().toISOString()
      };

      setSessions(prev => prev.map(s => {
        if (s.id === activeSessionId) {
          return {
            ...s,
            messages: [...s.messages, aiMessage]
          };
        }
        return s;
      }));

    } catch (error) {
      console.warn('API call failed, generating smart fallback response:', error);
      
      // Smart fallback response
      let fallbackText = '';
      if (activeTool === 'resume') {
        fallbackText = "📄 **Resume Scanner (Offline Mode)**\n\nCurrently offline, but here is standard resume feedback for MIT students:\n- Use standard sections: Education, Experience, Projects, Skills.\n- Avoid rating bars for skills; list them cleanly.\n- Keep it in PDF format.";
      } else if (activeTool === 'interview') {
        fallbackText = "🎙️ **Interview Mode (Offline Mode)**\n\nLet's practice behavioral questions. Question: *\"Tell me about a time you worked in a team and faced a conflict. How did you resolve it?\"*";
      } else {
        fallbackText = `🤖 **Campus Assistant (Offline Mode)**\n\nI received your query: "${text}".\n\n*Note: The backend API is currently unreachable, but I am here in offline fallback mode to assist you.*`;
      }

      const aiMessage: Message = {
        id: Math.random().toString(36).substring(2, 11),
        sender: 'ai',
        text: fallbackText,
        timestamp: new Date().toISOString(),
        isError: true
      };

      setSessions(prev => prev.map(s => {
        if (s.id === activeSessionId) {
          return {
            ...s,
            messages: [...s.messages, aiMessage]
          };
        }
        return s;
      }));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ChatContext.Provider
      value={{
        sessions,
        activeSessionId,
        isLoading,
        createSession,
        deleteSession,
        sendMessage,
        setActiveSessionId,
        activeSession
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
}
