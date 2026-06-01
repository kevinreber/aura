import { useEffect, useRef, useState } from 'react';
import { redirect, useSearchParams } from 'react-router';
import { useDarkMode } from '../hooks/useDarkMode';
import { getUser } from '../lib/auth.server';
import type { Route } from './+types/login';

export function meta() {
  return [
    { title: 'Sign in · Aura' },
    { name: 'description', content: 'Sign in to open your Aura daily dashboard.' },
  ];
}

export async function loader({ request }: Route.LoaderArgs) {
  const user = await getUser(request);
  if (user) throw redirect('/');
  return null;
}

const ERROR_MESSAGES: Record<string, string> = {
  not_authorized: 'This account is not authorized to use Aura.',
  invalid_state: 'Your sign-in attempt expired or was tampered with. Please try again.',
  token_exchange_failed: 'Google sign-in failed. Please try again.',
  userinfo_failed: 'Could not load your Google account info. Please try again.',
  unverified_email: 'Your Google email is not verified.',
  access_denied: 'Sign-in was cancelled.',
};

const FEATURES = [
  {
    title: 'Weather & Commute',
    desc: 'Forecasts, traffic, and transit options for your day.',
    icon: (
      <path d="M8 16.5a3.5 3.5 0 0 1-.3-6.98M15 9.2a4 4 0 0 1 2.6 7.3M12 2.5v1.4M6.5 4.8l1 1M17.5 4.8l-1 1M3.5 10.5h1.4" />
    ),
  },
  {
    title: 'Calendar & Tasks',
    desc: 'Your schedule and Todoist tasks at a glance.',
    icon: (
      <>
        <path d="M3 8.5h18" />
        <rect x="3" y="4.5" width="18" height="16" rx="2" />
        <path d="M8 2.5v4M16 2.5v4" />
      </>
    ),
  },
  {
    title: 'Markets',
    desc: 'Real-time tracking for stocks and crypto holdings.',
    icon: (
      <>
        <path d="M3 16.5l5.5-5.5 3.5 3.5L21 6.5" />
        <path d="M15.5 6.5H21v5.5" />
      </>
    ),
  },
  {
    title: 'AI Assistant',
    desc: 'Ask anything — your data is already in context.',
    icon: (
      <>
        <rect x="4" y="8" width="16" height="12" rx="3" />
        <path d="M12 8V4.5" />
        <circle cx="12" cy="3.5" r="1" />
        <path d="M9 13.5h.01M15 13.5h.01M2 13v3M22 13v3" />
      </>
    ),
  },
];

const PROMPTS = [
  'What’s my day look like?',
  'Will I need an umbrella this morning?',
  'How’s my portfolio doing today?',
  'Fastest route to the office right now?',
  'Summarize my unfinished tasks.',
];

function useGreeting() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 20_000);
    return () => clearInterval(id);
  }, []);
  const h = now.getHours();
  const greeting =
    h < 5
      ? 'Burning the midnight oil'
      : h < 12
        ? 'Good morning'
        : h < 18
          ? 'Good afternoon'
          : 'Good evening';
  const time = now.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  return { greeting, time };
}

// Typewriter that cycles through PROMPTS. Honors prefers-reduced-motion.
function useTypedPrompt() {
  const [text, setText] = useState('');
  useEffect(() => {
    if (
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ) {
      setText(PROMPTS[0]);
      return;
    }
    let pi = 0;
    let ci = 0;
    let deleting = false;
    let timer: ReturnType<typeof setTimeout>;
    const step = () => {
      const full = PROMPTS[pi];
      if (!deleting) {
        ci++;
        setText(full.slice(0, ci));
        if (ci === full.length) {
          deleting = true;
          timer = setTimeout(step, 1900);
          return;
        }
        timer = setTimeout(step, 45 + Math.random() * 45);
      } else {
        ci--;
        setText(full.slice(0, ci));
        if (ci === 0) {
          deleting = false;
          pi = (pi + 1) % PROMPTS.length;
          timer = setTimeout(step, 320);
          return;
        }
        timer = setTimeout(step, 22);
      }
    };
    timer = setTimeout(step, 650);
    return () => clearTimeout(timer);
  }, []);
  return text;
}

export default function Login() {
  const [searchParams] = useSearchParams();
  const errorCode = searchParams.get('error');
  const errorMessage = errorCode
    ? ERROR_MESSAGES[errorCode] || `Sign-in error: ${errorCode}`
    : null;

  const { isDark, setTheme } = useDarkMode();
  const { greeting, time } = useGreeting();
  const typed = useTypedPrompt();

  // Entrance stagger — flips on after mount so SSR markup is visible too.
  const [entered, setEntered] = useState(false);
  const raf = useRef<number | null>(null);
  useEffect(() => {
    raf.current = requestAnimationFrame(() => setEntered(true));
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, []);
  const rise = `transition-all duration-700 ease-out ${entered ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`;
  const delay = (ms: number) => ({ transitionDelay: `${ms}ms` });

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      {/* Ambient gradient background */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 right-10 h-[30rem] w-[30rem] rounded-full bg-indigo-400/10 blur-3xl dark:bg-indigo-600/10" />
        <div className="absolute -bottom-40 left-0 h-[28rem] w-[28rem] rounded-full bg-fuchsia-400/10 blur-3xl dark:bg-fuchsia-600/10" />
      </div>
      {/* Faint grid texture */}
      <div
        className="pointer-events-none fixed inset-0 opacity-50 dark:opacity-40"
        style={{
          backgroundImage:
            'linear-gradient(currentColor 1px, transparent 1px), linear-gradient(90deg, currentColor 1px, transparent 1px)',
          backgroundSize: '64px 64px',
          color: 'rgb(148 163 184 / 0.12)',
          maskImage: 'radial-gradient(72% 70% at 50% 38%, #000 0%, transparent 78%)',
          WebkitMaskImage: 'radial-gradient(72% 70% at 50% 38%, #000 0%, transparent 78%)',
        }}
      />

      {/* Theme toggle — segmented sun / moon */}
      <div
        className="fixed right-5 top-5 z-10 inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white/80 p-1 shadow-sm backdrop-blur dark:border-white/10 dark:bg-white/5"
        role="group"
        aria-label="Theme"
      >
        <button
          type="button"
          onClick={() => setTheme('light')}
          aria-pressed={!isDark}
          aria-label="Switch to light mode"
          title="Light mode"
          className={`flex h-7 w-7 items-center justify-center rounded-full transition-colors ${
            !isDark
              ? 'bg-slate-100 text-amber-500 shadow-sm dark:bg-white/10 dark:text-amber-400'
              : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
          }`}
        >
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
            <path
              fillRule="evenodd"
              d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z"
              clipRule="evenodd"
            />
          </svg>
        </button>
        <button
          type="button"
          onClick={() => setTheme('dark')}
          aria-pressed={isDark}
          aria-label="Switch to dark mode"
          title="Dark mode"
          className={`flex h-7 w-7 items-center justify-center rounded-full transition-colors ${
            isDark
              ? 'bg-slate-100 text-slate-900 shadow-sm dark:bg-white/10 dark:text-slate-100'
              : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
          }`}
        >
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
            <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
          </svg>
        </button>
      </div>

      {/* Layout */}
      <div className="relative mx-auto grid min-h-screen max-w-6xl items-center gap-12 px-6 py-16 lg:grid-cols-[1.1fr_0.9fr] lg:gap-20">
        {/* LEFT — hero */}
        <section>
          {/* greeting + clock */}
          <div
            className={`mb-6 inline-flex items-center gap-2.5 rounded-full border border-slate-200 bg-white/60 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-slate-500 backdrop-blur dark:border-white/10 dark:bg-white/5 dark:text-slate-400 ${rise}`}
            style={delay(40)}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-500 shadow-[0_0_0_3px] shadow-indigo-500/20" />
            <span>{greeting}</span>
            <span className="opacity-40">·</span>
            <span className="tabular-nums text-slate-700 dark:text-slate-300">{time}</span>
          </div>

          {/* brand */}
          <div className={`mb-8 flex items-center gap-3 ${rise}`} style={delay(90)}>
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 via-fuchsia-500 to-cyan-400 shadow-md shadow-indigo-500/30">
              <svg
                className="h-5 w-5 text-white"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" />
              </svg>
              <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-white/20 to-transparent" />
            </div>
            <span className="text-lg font-semibold tracking-tight">Aura</span>
          </div>

          <h1
            className={`text-4xl font-bold leading-[0.98] tracking-tight sm:text-5xl lg:text-6xl ${rise}`}
            style={delay(140)}
          >
            Your daily agent,
            <br />
            <span className="bg-gradient-to-r from-indigo-500 via-fuchsia-500 to-cyan-400 bg-clip-text text-transparent">
              always in context.
            </span>
          </h1>

          <p
            className={`mt-5 max-w-xl text-pretty text-base leading-relaxed text-slate-600 dark:text-slate-400 sm:text-lg ${rise}`}
            style={delay(190)}
          >
            A personal AI dashboard that pulls your weather, calendar, tasks, markets and commute
            into one place — then lets you chat with it.
          </p>

          {/* typed demo */}
          <div
            className={`mt-7 flex max-w-xl items-center gap-3 rounded-2xl border border-slate-200/70 bg-white/70 p-3.5 shadow-sm backdrop-blur dark:border-white/10 dark:bg-white/[0.04] ${rise}`}
            style={delay(240)}
          >
            <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-indigo-100 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-300">
              <svg
                className="h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" />
              </svg>
            </span>
            <span className="min-h-[1.3em] text-sm text-slate-800 dark:text-slate-100">
              {typed}
              <span className="ml-0.5 inline-block h-[1em] w-0.5 -translate-y-px animate-pulse bg-indigo-500 align-middle" />
            </span>
          </div>

          {/* features */}
          <div className="mt-8 grid max-w-xl grid-cols-1 gap-3 sm:grid-cols-2">
            {FEATURES.map((f, i) => (
              <div
                key={f.title}
                className={`group flex gap-3 rounded-2xl border border-slate-200/70 bg-white/70 p-4 shadow-sm backdrop-blur transition-all hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md dark:border-white/10 dark:bg-white/[0.04] dark:hover:border-white/20 ${rise}`}
                style={delay(300 + i * 70)}
              >
                <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-indigo-100 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-300">
                  <svg
                    className="h-[18px] w-[18px]"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    {f.icon}
                  </svg>
                </span>
                <div className="min-w-0">
                  <div className="text-sm font-semibold tracking-tight text-slate-900 dark:text-white">
                    {f.title}
                  </div>
                  <div className="mt-0.5 text-xs leading-snug text-slate-500 dark:text-slate-400">
                    {f.desc}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* RIGHT — sign-in card */}
        <section
          className={`relative overflow-hidden rounded-3xl border border-slate-200/80 bg-white/80 p-7 shadow-xl shadow-slate-200/50 backdrop-blur-xl dark:border-white/10 dark:bg-white/[0.05] dark:shadow-black/40 sm:p-8 ${rise}`}
          style={delay(360)}
        >
          {/* top accent edge */}
          <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-indigo-500/60 to-transparent" />
          {/* soft glow */}
          <div className="pointer-events-none absolute -top-24 left-1/2 h-56 w-56 -translate-x-1/2 rounded-full bg-indigo-400/20 blur-3xl dark:bg-indigo-500/15" />

          <div className="relative">
            <div className="mb-5 inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 shadow-[0_0_0_3px] shadow-emerald-500/20" />
              Private · Single-user
            </div>

            <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              Welcome back
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
              Sign in with your Google account to open your dashboard.
            </p>

            {errorMessage && (
              <div
                className="mt-5 flex items-start gap-2 rounded-xl border border-red-500/30 bg-red-50 px-3 py-2.5 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-200"
                role="alert"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="mt-0.5 h-4 w-4 flex-shrink-0"
                  aria-hidden="true"
                >
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
                <span>{errorMessage}</span>
              </div>
            )}

            {/* OAuth trigger — GET to the consent initiator route */}
            <a
              href="/auth/google"
              className="group mt-6 flex w-full items-center justify-center gap-3 rounded-xl bg-white px-4 py-3.5 text-sm font-semibold text-slate-800 shadow-[0_2px_8px_rgba(0,0,0,0.18)] ring-1 ring-slate-200 transition-all hover:-translate-y-0.5 hover:shadow-[0_6px_18px_rgba(0,0,0,0.22)] dark:ring-0"
            >
              <svg className="h-[18px] w-[18px] flex-shrink-0" viewBox="0 0 48 48" aria-hidden="true">
                <path
                  fill="#EA4335"
                  d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
                />
                <path
                  fill="#4285F4"
                  d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
                />
                <path
                  fill="#FBBC05"
                  d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
                />
                <path
                  fill="#34A853"
                  d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
                />
              </svg>
              Continue with Google
              <svg
                className="h-4 w-4 text-slate-400 transition-transform group-hover:translate-x-0.5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </a>

            <div className="mt-5 flex items-start gap-2.5 border-t border-slate-200 pt-5 text-xs leading-relaxed text-slate-500 dark:border-white/10 dark:text-slate-400">
              <svg
                className="mt-px h-3.5 w-3.5 flex-shrink-0 text-slate-400 dark:text-slate-500"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <rect x="4" y="10.5" width="16" height="10" rx="2.5" />
                <path d="M8 10.5V8a4 4 0 0 1 8 0v2.5" />
              </svg>
              <span>
                Access is limited to allowlisted Google accounts. Your data stays in your account.
              </span>
            </div>

            <div className="mt-5 text-center font-mono text-[10px] tracking-wider text-slate-400 dark:text-slate-600">
              Made with care · v1.0
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
