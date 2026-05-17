import { redirect, useSearchParams } from 'react-router';
import { getUser } from '../lib/auth.server';
import type { Route } from './+types/login';

export function meta() {
  return [{ title: 'Sign in · Aura' }];
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
    icon: '🌤️',
    title: 'Weather & Commute',
    description: 'Forecasts, traffic, and transit options for your day.',
  },
  {
    icon: '📅',
    title: 'Calendar & Tasks',
    description: 'See your schedule and Todoist tasks at a glance.',
  },
  {
    icon: '💰',
    title: 'Markets',
    description: 'Real-time tracking for stocks and crypto holdings.',
  },
  {
    icon: '🤖',
    title: 'AI Assistant',
    description: 'Ask anything — your data is already in context.',
  },
];

export default function Login() {
  const [searchParams] = useSearchParams();
  const errorCode = searchParams.get('error');
  const errorMessage = errorCode
    ? ERROR_MESSAGES[errorCode] || `Sign-in error: ${errorCode}`
    : null;

  return (
    <main className="relative min-h-screen overflow-hidden bg-slate-950 text-white">
      {/* Aurora background: layered radial gradients + subtle animated blobs */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 h-[36rem] w-[36rem] rounded-full bg-indigo-600/30 blur-3xl animate-pulse" />
        <div
          className="absolute top-1/3 -right-32 h-[32rem] w-[32rem] rounded-full bg-fuchsia-600/20 blur-3xl animate-pulse"
          style={{ animationDelay: '1.5s' }}
        />
        <div
          className="absolute -bottom-40 left-1/4 h-[34rem] w-[34rem] rounded-full bg-cyan-500/20 blur-3xl animate-pulse"
          style={{ animationDelay: '3s' }}
        />
        {/* Grid pattern overlay */}
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage:
              'linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />
      </div>

      <div className="relative z-10 mx-auto flex min-h-screen max-w-6xl flex-col items-center justify-center px-6 py-12 lg:flex-row lg:items-stretch lg:gap-16 lg:py-16">
        {/* Left: Brand + Features */}
        <section className="flex flex-1 flex-col justify-center text-center lg:text-left">
          <div className="mb-6 flex items-center justify-center gap-3 lg:justify-start">
            <div className="relative flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 via-fuchsia-500 to-cyan-400 shadow-lg shadow-indigo-500/30">
              <span className="text-2xl" aria-hidden="true">
                ✨
              </span>
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-white/20 to-transparent" />
            </div>
            <span className="text-2xl font-semibold tracking-tight">Aura</span>
          </div>

          <h1 className="bg-gradient-to-br from-white via-white to-white/60 bg-clip-text text-4xl font-bold leading-tight tracking-tight text-transparent sm:text-5xl lg:text-6xl">
            Your daily agent,
            <br />
            <span className="bg-gradient-to-r from-indigo-300 via-fuchsia-300 to-cyan-300 bg-clip-text text-transparent">
              always in context.
            </span>
          </h1>

          <p className="mx-auto mt-5 max-w-md text-base text-slate-300 sm:text-lg lg:mx-0">
            A personal AI dashboard that pulls your weather, calendar, tasks, markets and commute
            into one place — then lets you chat with it.
          </p>

          <div className="mt-10 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:max-w-lg">
            {FEATURES.map((feature) => (
              <div
                key={feature.title}
                className="group flex items-start gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-3 text-left backdrop-blur-sm transition-colors hover:border-white/20 hover:bg-white/[0.06]"
              >
                <span className="text-xl" aria-hidden="true">
                  {feature.icon}
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-white">{feature.title}</p>
                  <p className="mt-0.5 text-xs text-slate-400">{feature.description}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Right: Sign-in card */}
        <section className="mt-12 flex w-full max-w-md flex-col justify-center lg:mt-0 lg:w-[26rem]">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-6 shadow-2xl shadow-black/40 backdrop-blur-xl sm:p-8">
            <div className="mb-1 flex items-center gap-2">
              <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
              <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                Private · Single-user
              </span>
            </div>

            <h2 className="text-2xl font-semibold text-white">Welcome back</h2>
            <p className="mt-1 text-sm text-slate-400">
              Sign in with your Google account to open your dashboard.
            </p>

            {errorMessage && (
              <div
                className="mt-5 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2.5 text-sm text-red-200"
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

            <a
              href="/auth/google"
              className="group mt-6 inline-flex w-full items-center justify-center gap-3 rounded-xl bg-white px-4 py-3 text-sm font-semibold text-slate-900 shadow-lg shadow-black/30 transition-all hover:bg-slate-100 hover:shadow-xl active:scale-[0.98]"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 48 48"
                className="h-5 w-5"
                aria-hidden="true"
              >
                <path
                  fill="#FFC107"
                  d="M43.6 20.5H42V20H24v8h11.3c-1.6 4.7-6.1 8-11.3 8-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.2-.1-2.3-.4-3.5z"
                />
                <path
                  fill="#FF3D00"
                  d="M6.3 14.7l6.6 4.8C14.7 16 19 13 24 13c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.4 6.3 14.7z"
                />
                <path
                  fill="#4CAF50"
                  d="M24 44c5.2 0 9.8-2 13.3-5.2l-6.1-5.2c-2 1.5-4.5 2.4-7.2 2.4-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.5 16.2 44 24 44z"
                />
                <path
                  fill="#1976D2"
                  d="M43.6 20.5H42V20H24v8h11.3c-.8 2.3-2.3 4.2-4.2 5.6l6.1 5.2C40.9 35.9 44 30.4 44 24c0-1.2-.1-2.3-.4-3.5z"
                />
              </svg>
              <span>Continue with Google</span>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-4 w-4 transition-transform group-hover:translate-x-0.5"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </a>

            <div className="mt-6 flex items-center gap-3 text-xs text-slate-500">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-4 w-4 flex-shrink-0 text-slate-400"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z"
                  clipRule="evenodd"
                />
              </svg>
              <span>
                Access is limited to allowlisted Google accounts. Your data stays in your account.
              </span>
            </div>
          </div>

          <p className="mt-6 text-center text-xs text-slate-500">
            Made with care · v1.0
          </p>
        </section>
      </div>
    </main>
  );
}
