"use client";

import { useEffect, useRef, useState } from 'react';
import type Vapi from '@vapi-ai/web';

/**
 * Gemini-Live–style mock interview, powered by the Vapi Web SDK.
 *
 * Flow: open → SETUP (pick interview parameters) → START → live voice↔voice call.
 * Vapi runs the full real-time loop (STT + LLM + TTS over WebRTC); this component
 * collects the candidate's preferences, passes them to the assistant as
 * `assistantOverrides.variableValues` (available as {{key}} inside the Vapi
 * assistant prompt), and renders an immersive overlay driven by Vapi events.
 *
 * Configure via Vercel/`.env`:
 *   NEXT_PUBLIC_VAPI_PUBLIC_KEY    – Vapi public (web) key
 *   NEXT_PUBLIC_VAPI_ASSISTANT_ID  – the interviewer assistant to dial
 */

type Phase = 'connecting' | 'listening' | 'speaking' | 'ended' | 'error';
type Turn = { role: 'user' | 'assistant'; content: string };

interface InterviewConfig {
  type: string;
  role: string;
  field: string;
  experience: string;
  difficulty: string;
  focus: string;
  company: string;
}

interface InterviewLiveProps {
  open: boolean;
  onClose: () => void;
}

interface VapiMessage {
  type?: string;
  role?: 'user' | 'assistant' | string;
  transcript?: string;
  transcriptType?: 'partial' | 'final' | string;
}

const PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY;
const ASSISTANT_ID = process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID;

const INTERVIEW_TYPES = ['Technical', 'Behavioral', 'HR / General', 'System Design', 'Case Study', 'Mixed'];
const FIELDS = ['Software Engineering', 'Data Science / ML', 'Product Management', 'Electronics / ECE', 'Mechanical', 'Finance', 'Consulting', 'Other'];
const EXPERIENCE_LEVELS = ['Final-year student / Fresher', 'Internship level', '0–2 years', '2–5 years', '5+ years'];
const DIFFICULTIES = ['Easy', 'Medium', 'Hard'];

const DEFAULT_CONFIG: InterviewConfig = {
  type: 'Technical',
  role: '',
  field: 'Software Engineering',
  experience: 'Final-year student / Fresher',
  difficulty: 'Medium',
  focus: '',
  company: '',
};

const PHASE_LABEL: Record<Phase, string> = {
  connecting: 'Connecting…',
  listening: 'Listening…',
  speaking: 'Interviewer speaking…',
  ended: 'Interview ended',
  error: 'Connection error',
};

function buildFirstMessage(cfg: InterviewConfig): string {
  const at = cfg.company.trim() ? ` for a role at ${cfg.company.trim()}` : '';
  return (
    `Hello! I'll be your interviewer today for a ${cfg.difficulty.toLowerCase()} ${cfg.type} interview ` +
    `for the ${cfg.role.trim() || 'candidate'} position in ${cfg.field}${at}. ` +
    `Let's begin — could you start by telling me a little about yourself?`
  );
}

export default function InterviewLive({ open, onClose }: InterviewLiveProps) {
  const [started, setStarted] = useState(false);
  const [config, setConfig] = useState<InterviewConfig>(DEFAULT_CONFIG);

  const [phase, setPhase] = useState<Phase>('connecting');
  const [transcript, setTranscript] = useState<Turn[]>([]);
  const [partialUser, setPartialUser] = useState('');
  const [partialAssistant, setPartialAssistant] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [muted, setMuted] = useState(false);

  const vapiRef = useRef<Vapi | null>(null);
  const orbRef = useRef<HTMLDivElement | null>(null);
  const configRef = useRef<InterviewConfig>(config);

  const setOrbLevel = (scale: number) => orbRef.current?.style.setProperty('--iv-level', String(scale));

  // Reset back to the setup form whenever the overlay is closed (deferred so no
  // setState runs synchronously inside the effect body).
  useEffect(() => {
    if (open) return;
    const id = setTimeout(() => setStarted(false), 0);
    return () => clearTimeout(id);
  }, [open]);

  // Live Vapi session — only runs once the user has started the interview.
  useEffect(() => {
    if (!open || !started) return;
    let cancelled = false;

    const run = async () => {
      if (!PUBLIC_KEY || !ASSISTANT_ID) {
        setErrorMsg('Voice service is not configured. Set NEXT_PUBLIC_VAPI_PUBLIC_KEY and NEXT_PUBLIC_VAPI_ASSISTANT_ID.');
        setPhase('error');
        return;
      }

      setPhase('connecting');
      setErrorMsg(null);
      setTranscript([]);
      setPartialUser('');
      setPartialAssistant('');
      setMuted(false);

      let VapiCtor: typeof Vapi;
      try {
        VapiCtor = (await import('@vapi-ai/web')).default;
      } catch (err) {
        console.error('Failed to load Vapi SDK:', err);
        if (!cancelled) { setErrorMsg('Could not load the voice SDK.'); setPhase('error'); }
        return;
      }
      if (cancelled) return;

      const vapi = new VapiCtor(PUBLIC_KEY);
      vapiRef.current = vapi;

      vapi.on('call-start', () => setPhase('listening'));
      vapi.on('call-end', () => { setOrbLevel(1); setPhase('ended'); });
      vapi.on('speech-start', () => setPhase('speaking'));
      vapi.on('speech-end', () => { setOrbLevel(1); setPhase((p) => (p === 'ended' || p === 'error' ? p : 'listening')); });
      vapi.on('volume-level', (volume: number) => setOrbLevel(1 + Math.min(volume * 1.4, 1.05)));
      vapi.on('error', (err: unknown) => {
        console.error('Vapi error:', err);
        const message = (err as { errorMsg?: string; message?: string })?.errorMsg
          ?? (err as { message?: string })?.message;
        setErrorMsg(typeof message === 'string' ? message : 'Voice connection error.');
        setPhase('error');
      });
      vapi.on('message', (message: VapiMessage) => {
        if (message?.type !== 'transcript' || typeof message.transcript !== 'string') return;
        const role: Turn['role'] = message.role === 'user' ? 'user' : 'assistant';
        const text = message.transcript;
        if (message.transcriptType === 'final') {
          setTranscript((prev) => [...prev, { role, content: text }]);
          if (role === 'user') setPartialUser(''); else setPartialAssistant('');
        } else if (role === 'user') {
          setPartialUser(text);
        } else {
          setPartialAssistant(text);
        }
      });

      // Pass the candidate's chosen parameters to the interviewer assistant.
      const cfg = configRef.current;
      const overrides: Parameters<typeof vapi.start>[1] = {
        variableValues: {
          interviewType: cfg.type,
          role: cfg.role.trim() || 'Software Engineer',
          field: cfg.field,
          experience: cfg.experience,
          difficulty: cfg.difficulty,
          focus: cfg.focus.trim() || 'general fundamentals',
          company: cfg.company.trim() || 'a top company',
        },
        firstMessage: buildFirstMessage(cfg),
      };

      try {
        await vapi.start(ASSISTANT_ID, overrides);
      } catch (err) {
        console.error('Vapi start failed:', err);
        if (!cancelled) {
          setErrorMsg('Could not start the interview call. Check your microphone permission and Vapi keys.');
          setPhase('error');
        }
      }
    };

    // Defer so no setState runs synchronously inside the effect body.
    Promise.resolve().then(() => { if (!cancelled) run(); });

    return () => {
      cancelled = true;
      const vapi = vapiRef.current;
      vapiRef.current = null;
      try { vapi?.removeAllListeners(); } catch { /* noop */ }
      try { vapi?.stop(); } catch { /* noop */ }
    };
  }, [open, started]);

  if (!open) return null;

  const updateConfig = (patch: Partial<InterviewConfig>) => setConfig((c) => ({ ...c, ...patch }));

  const startInterview = () => {
    configRef.current = config;
    setStarted(true);
  };

  const toggleMute = () => {
    const next = !muted;
    setMuted(next);
    try { vapiRef.current?.setMuted(next); } catch { /* noop */ }
  };

  const end = () => {
    try { vapiRef.current?.stop(); } catch { /* noop */ }
    setStarted(false);
    onClose();
  };

  // ── Setup view ────────────────────────────────────────────────────────────
  if (!started) {
    const inputClass =
      'w-full rounded-xl bg-white/5 border border-white/15 px-3.5 py-2.5 text-sm text-white ' +
      'placeholder-white/30 focus:outline-none focus:border-manipal-orange/70 transition-colors';
    return (
      <div
        className="fixed inset-0 z-50 flex flex-col items-center text-white overflow-y-auto"
        style={{ background: 'radial-gradient(120% 90% at 50% 0%, #1a1033 0%, #0b1020 55%, #05060d 100%)' }}
      >
        <div className="pointer-events-none absolute -top-24 -left-16 w-96 h-96 rounded-full opacity-25 blur-3xl"
             style={{ background: '#f37021', animation: 'orbDrift1 14s ease-in-out infinite' }} />

        <div className="w-full max-w-lg px-6 py-8 z-10" style={{ animation: 'ivFadeIn 0.4s ease' }}>
          <div className="flex items-start justify-between mb-6">
            <div>
              <h2 className="text-xl font-semibold">Set up your interview</h2>
              <p className="text-[12px] text-white/50 mt-1">These preferences are sent to your interviewer.</p>
            </div>
            <button
              type="button"
              onClick={end}
              className="w-9 h-9 rounded-full bg-white/10 hover:bg-white/20 border border-white/15 flex items-center justify-center transition-colors cursor-pointer"
              title="Close"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-[11px] uppercase tracking-wide text-white/45 mb-1.5">Interview type</label>
              <div className="flex flex-wrap gap-2">
                {INTERVIEW_TYPES.map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => updateConfig({ type: t })}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all cursor-pointer ${
                      config.type === t
                        ? 'bg-manipal-orange border-manipal-orange text-white'
                        : 'bg-white/5 border-white/15 text-white/70 hover:border-white/30'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-[11px] uppercase tracking-wide text-white/45 mb-1.5">Role / Position</label>
              <input
                className={inputClass}
                value={config.role}
                onChange={(e) => updateConfig({ role: e.target.value })}
                placeholder="e.g. Software Engineer, Data Analyst"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] uppercase tracking-wide text-white/45 mb-1.5">Field</label>
                <select
                  className={`${inputClass} appearance-none cursor-pointer`}
                  value={config.field}
                  onChange={(e) => updateConfig({ field: e.target.value })}
                >
                  {FIELDS.map((f) => <option key={f} value={f} className="bg-[#1a1033]">{f}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-[11px] uppercase tracking-wide text-white/45 mb-1.5">Difficulty</label>
                <select
                  className={`${inputClass} appearance-none cursor-pointer`}
                  value={config.difficulty}
                  onChange={(e) => updateConfig({ difficulty: e.target.value })}
                >
                  {DIFFICULTIES.map((d) => <option key={d} value={d} className="bg-[#1a1033]">{d}</option>)}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-[11px] uppercase tracking-wide text-white/45 mb-1.5">Experience level</label>
              <select
                className={`${inputClass} appearance-none cursor-pointer`}
                value={config.experience}
                onChange={(e) => updateConfig({ experience: e.target.value })}
              >
                {EXPERIENCE_LEVELS.map((x) => <option key={x} value={x} className="bg-[#1a1033]">{x}</option>)}
              </select>
            </div>

            <div>
              <label className="block text-[11px] uppercase tracking-wide text-white/45 mb-1.5">Focus areas <span className="normal-case text-white/30">(optional)</span></label>
              <input
                className={inputClass}
                value={config.focus}
                onChange={(e) => updateConfig({ focus: e.target.value })}
                placeholder="e.g. DSA, OOP, DBMS, System Design"
              />
            </div>

            <div>
              <label className="block text-[11px] uppercase tracking-wide text-white/45 mb-1.5">Target company <span className="normal-case text-white/30">(optional)</span></label>
              <input
                className={inputClass}
                value={config.company}
                onChange={(e) => updateConfig({ company: e.target.value })}
                placeholder="e.g. Google, JP Morgan"
              />
            </div>
          </div>

          <button
            type="button"
            onClick={startInterview}
            disabled={!config.role.trim()}
            className="mt-7 w-full py-3 rounded-xl bg-manipal-orange hover:bg-orange-600 text-white font-semibold text-sm transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
            Start Interview
          </button>
          {!config.role.trim() && (
            <p className="text-center text-[11px] text-white/40 mt-2">Enter a role to begin.</p>
          )}
        </div>
      </div>
    );
  }

  // ── Live call view ────────────────────────────────────────────────────────
  const lastUserFinal = [...transcript].reverse().find((t) => t.role === 'user')?.content ?? '';
  const lastBotFinal = [...transcript].reverse().find((t) => t.role === 'assistant')?.content ?? '';
  const botLine = partialAssistant || lastBotFinal;
  const userLine = partialUser || lastUserFinal;

  const accent =
    phase === 'speaking' ? '#ed1c24' :
    phase === 'listening' ? '#f37021' :
    phase === 'ended' ? '#94a3b8' :
    phase === 'error' ? '#ef4444' : '#f59e0b';

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col items-center text-white overflow-hidden"
      style={{ background: 'radial-gradient(120% 90% at 50% 0%, #1a1033 0%, #0b1020 55%, #05060d 100%)' }}
    >
      {/* Ambient drifting glows */}
      <div className="pointer-events-none absolute -top-24 -left-16 w-96 h-96 rounded-full opacity-30 blur-3xl"
           style={{ background: '#f37021', animation: 'orbDrift1 14s ease-in-out infinite' }} />
      <div className="pointer-events-none absolute bottom-0 -right-20 w-[28rem] h-[28rem] rounded-full opacity-20 blur-3xl"
           style={{ background: '#ed1c24', animation: 'orbDrift2 18s ease-in-out infinite' }} />

      {/* Top bar */}
      <div className="w-full flex items-center justify-between px-6 py-4 z-10 shrink-0">
        <div className="flex items-center gap-2.5">
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: accent, boxShadow: `0 0 10px ${accent}` }} />
          <div className="leading-tight">
            <p className="text-sm font-semibold tracking-wide">Interview Mode · Live</p>
            <p className="text-[11px] text-white/50">{config.type} · {config.role.trim() || config.field}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={end}
          className="w-9 h-9 rounded-full bg-white/10 hover:bg-white/20 border border-white/15 flex items-center justify-center transition-colors cursor-pointer"
          title="End interview"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Center: orb + captions */}
      <div className="flex-1 w-full flex flex-col items-center justify-center px-6 z-10 min-h-0">
        <div className="relative flex items-center justify-center" style={{ width: 260, height: 260 }}>
          {(phase === 'listening' || phase === 'speaking') &&
            [0, 1, 2].map((i) => (
              <span
                key={i}
                className="absolute rounded-full"
                style={{ width: 200, height: 200, background: accent, animation: `ivRingPulse 2.6s ${i * 0.85}s ease-out infinite` }}
              />
            ))}

          <div
            ref={orbRef}
            className="relative rounded-full"
            style={{
              width: 168, height: 168,
              background: 'radial-gradient(circle at 35% 28%, #ffd9b0 0%, #f37021 46%, #c92b1e 100%)',
              boxShadow: `0 0 70px ${accent}aa, inset 0 0 40px rgba(255,255,255,0.12)`,
              transform: 'scale(var(--iv-level, 1))',
              transition: 'transform 90ms linear',
              animation:
                phase === 'speaking' ? 'ivBreathe 1.5s ease-in-out infinite'
                : phase === 'connecting' ? 'ivBreathe 2.6s ease-in-out infinite'
                : undefined,
            }}
          >
            {phase === 'connecting' && (
              <div
                className="absolute inset-0 rounded-full"
                style={{
                  background: 'conic-gradient(from 0deg, transparent, rgba(255,255,255,0.55), transparent)',
                  animation: 'ivSpinSlow 1.3s linear infinite',
                  mixBlendMode: 'overlay',
                }}
              />
            )}
          </div>
        </div>

        {/* Status */}
        <p className="mt-7 text-sm font-medium tracking-wide" style={{ color: accent }}>
          {muted && phase !== 'error' && phase !== 'ended' ? 'Muted' : PHASE_LABEL[phase]}
        </p>

        {/* Captions */}
        <div className="mt-4 w-full max-w-2xl text-center min-h-[5.5rem]">
          {phase === 'error' ? (
            <p className="text-sm text-red-300">{errorMsg}</p>
          ) : phase === 'ended' && !botLine ? (
            <p className="text-sm text-white/60">Thanks for interviewing. You can close this and review your chat.</p>
          ) : (
            <>
              {botLine && (
                <p key={botLine} className="text-lg md:text-xl font-light leading-relaxed text-white/95"
                   style={{ animation: 'ivFadeIn 0.4s ease' }}>
                  {botLine}
                </p>
              )}
              {userLine && <p className="mt-3 text-sm text-white/45 italic">“{userLine}”</p>}
            </>
          )}
        </div>
      </div>

      {/* Controls */}
      <div className="w-full flex items-center justify-center gap-4 px-6 py-7 z-10 shrink-0">
        <button
          type="button"
          onClick={toggleMute}
          disabled={phase === 'error' || phase === 'ended'}
          className={`w-16 h-16 rounded-full flex items-center justify-center transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${
            muted ? 'bg-white/15 hover:bg-white/25 border border-white/20' : 'bg-manipal-orange hover:bg-orange-600'
          }`}
          title={muted ? 'Unmute microphone' : 'Mute microphone'}
        >
          {muted ? (
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z M17 9l4 4m0-4l-4 4" />
            </svg>
          ) : (
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m-4 0h8m-8-8a3 3 0 003 3 3 3 0 003-3V5a3 3 0 10-6 0v6z" />
            </svg>
          )}
        </button>

        <button
          type="button"
          onClick={end}
          className="w-12 h-12 rounded-full bg-red-500 hover:bg-red-600 flex items-center justify-center transition-colors cursor-pointer"
          title="End interview"
        >
          <svg className="w-5 h-5 rotate-[135deg]" fill="currentColor" viewBox="0 0 24 24">
            <path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.18z" />
          </svg>
        </button>
      </div>
    </div>
  );
}
