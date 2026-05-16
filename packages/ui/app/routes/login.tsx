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

export default function Login() {
  const [searchParams] = useSearchParams();
  const errorCode = searchParams.get('error');
  const errorMessage = errorCode
    ? ERROR_MESSAGES[errorCode] || `Sign-in error: ${errorCode}`
    : null;

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
      <div className="w-full max-w-sm bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 sm:p-8">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mb-1">
          Welcome to Aura
        </h1>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
          Sign in with your Google account to continue.
        </p>

        {errorMessage && (
          <div
            className="mb-4 rounded-lg border border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-900/30 dark:text-red-200 px-3 py-2 text-sm"
            role="alert"
          >
            {errorMessage}
          </div>
        )}

        <a
          href="/auth/google"
          className="w-full inline-flex items-center justify-center gap-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 48 48"
            className="w-5 h-5"
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
          Sign in with Google
        </a>

        <p className="mt-6 text-xs text-gray-500 dark:text-gray-400">
          Access is limited to allowlisted Google accounts.
        </p>
      </div>
    </main>
  );
}
