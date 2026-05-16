/**
 * Cookie-based session storage for Google OAuth.
 *
 * Server-only — this file imports `react-router` server APIs and must never
 * be bundled into the browser. The `.server.ts` suffix ensures Vite/RR
 * excludes it from the client bundle.
 */

import { createCookieSessionStorage } from 'react-router';

export type SessionUser = {
  email: string;
  name: string;
  picture?: string;
};

const SESSION_SECRET = process.env.SESSION_SECRET;

if (!SESSION_SECRET && process.env.NODE_ENV === 'production') {
  throw new Error('SESSION_SECRET must be set in production');
}

// Default to Secure cookies; explicit opt-out for local HTTP dev only.
// NODE_ENV is unreliable for runtime security decisions (some platforms set
// it only at build time, custom envs like 'staging'/'preview' would also
// silently strip Secure). Dedicated env keeps the signal explicit.
const SECURE_COOKIES = process.env.SESSION_COOKIE_SECURE !== 'false';

export const sessionStorage = createCookieSessionStorage<{
  user: SessionUser;
  oauthState: string;
}>({
  cookie: {
    name: 'aura_session',
    httpOnly: true,
    path: '/',
    sameSite: 'lax',
    secrets: [SESSION_SECRET || 'dev-only-insecure-secret-change-me'],
    secure: SECURE_COOKIES,
    maxAge: 60 * 60 * 24 * 7, // 1 week
  },
});

export const { getSession, commitSession, destroySession } = sessionStorage;
