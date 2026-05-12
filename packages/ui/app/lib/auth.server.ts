/**
 * Google OAuth + single-user allowlist.
 *
 * Flow:
 *   1. /auth/google           → build Google OAuth URL, store state in session, redirect
 *   2. /auth/google/callback  → verify state, exchange code, fetch userinfo,
 *                                check email against ALLOWED_EMAILS, set session
 *   3. /auth/logout           → destroy session
 *
 * Server-only.
 */

import { redirect } from 'react-router';
import { commitSession, destroySession, getSession, type SessionUser } from './session.server';

const GOOGLE_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/v2/auth';
const GOOGLE_TOKEN_ENDPOINT = 'https://oauth2.googleapis.com/token';
const GOOGLE_USERINFO_ENDPOINT = 'https://www.googleapis.com/oauth2/v2/userinfo';

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function getRedirectUri(request: Request): string {
  // Allow explicit override (useful behind a proxy / in production).
  const override = process.env.GOOGLE_REDIRECT_URI;
  if (override) return override;
  const url = new URL(request.url);
  return `${url.origin}/auth/google/callback`;
}

function getAllowedEmails(): Set<string> {
  const raw = process.env.ALLOWED_EMAILS || '';
  return new Set(
    raw
      .split(',')
      .map((e) => e.trim().toLowerCase())
      .filter(Boolean)
  );
}

export function isEmailAllowed(email: string): boolean {
  const allowlist = getAllowedEmails();
  if (allowlist.size === 0) {
    // Fail closed: with no allowlist configured, no one gets in.
    return false;
  }
  return allowlist.has(email.toLowerCase());
}

/**
 * Build the Google OAuth consent URL and persist a CSRF state token in the
 * session cookie. Returns a redirect response.
 */
export async function startGoogleOAuth(request: Request): Promise<Response> {
  const clientId = requiredEnv('GOOGLE_CLIENT_ID');
  const redirectUri = getRedirectUri(request);

  // CSRF state — random token bound to the session cookie.
  const state = crypto.randomUUID();
  const session = await getSession(request.headers.get('Cookie'));
  session.set('oauthState', state);

  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: 'code',
    scope: 'openid email profile',
    state,
    access_type: 'online',
    prompt: 'select_account',
  });

  return redirect(`${GOOGLE_AUTH_ENDPOINT}?${params.toString()}`, {
    headers: { 'Set-Cookie': await commitSession(session) },
  });
}

type GoogleTokenResponse = {
  access_token: string;
  expires_in: number;
  token_type: string;
  id_token?: string;
  scope?: string;
};

type GoogleUserInfo = {
  id: string;
  email: string;
  verified_email: boolean;
  name: string;
  given_name?: string;
  family_name?: string;
  picture?: string;
};

/**
 * Handle the Google OAuth redirect: verify state, exchange code for token,
 * fetch userinfo, check the allowlist, and set a logged-in session.
 */
export async function handleGoogleCallback(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const code = url.searchParams.get('code');
  const state = url.searchParams.get('state');
  const errorParam = url.searchParams.get('error');

  const session = await getSession(request.headers.get('Cookie'));
  const expectedState = session.get('oauthState');

  if (errorParam) {
    return redirect(`/login?error=${encodeURIComponent(errorParam)}`);
  }

  if (!code || !state || !expectedState || state !== expectedState) {
    return redirect('/login?error=invalid_state');
  }

  // One-shot: clear the state regardless of success.
  session.unset('oauthState');

  const clientId = requiredEnv('GOOGLE_CLIENT_ID');
  const clientSecret = requiredEnv('GOOGLE_CLIENT_SECRET');
  const redirectUri = getRedirectUri(request);

  const tokenResp = await fetch(GOOGLE_TOKEN_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      code,
      client_id: clientId,
      client_secret: clientSecret,
      redirect_uri: redirectUri,
      grant_type: 'authorization_code',
    }),
  });

  if (!tokenResp.ok) {
    console.error('Google token exchange failed:', await tokenResp.text());
    return redirect('/login?error=token_exchange_failed');
  }

  const tokens = (await tokenResp.json()) as GoogleTokenResponse;

  const userResp = await fetch(GOOGLE_USERINFO_ENDPOINT, {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  });

  if (!userResp.ok) {
    console.error('Google userinfo fetch failed:', await userResp.text());
    return redirect('/login?error=userinfo_failed');
  }

  const userInfo = (await userResp.json()) as GoogleUserInfo;

  if (!userInfo.verified_email) {
    return redirect('/login?error=unverified_email');
  }

  if (!isEmailAllowed(userInfo.email)) {
    console.warn(`Login rejected for non-allowlisted email: ${userInfo.email}`);
    // Don't set the session — force a logout-state redirect.
    return redirect('/login?error=not_authorized', {
      headers: { 'Set-Cookie': await destroySession(session) },
    });
  }

  const user: SessionUser = {
    email: userInfo.email,
    name: userInfo.name,
    picture: userInfo.picture,
  };
  session.set('user', user);

  return redirect('/', {
    headers: { 'Set-Cookie': await commitSession(session) },
  });
}

export async function logout(request: Request): Promise<Response> {
  const session = await getSession(request.headers.get('Cookie'));
  return redirect('/login', {
    headers: { 'Set-Cookie': await destroySession(session) },
  });
}

/**
 * Read the current user from the session, or null if not logged in / not
 * allowlisted. Re-checks the allowlist on every request so removing an email
 * from ALLOWED_EMAILS immediately invalidates existing sessions.
 */
export async function getUser(request: Request): Promise<SessionUser | null> {
  const session = await getSession(request.headers.get('Cookie'));
  const user = session.get('user');
  if (!user) return null;
  if (!isEmailAllowed(user.email)) return null;
  return user;
}

/**
 * For loaders / actions: require a logged-in user, or redirect to /login.
 */
export async function requireUser(request: Request): Promise<SessionUser> {
  const user = await getUser(request);
  if (!user) throw redirect('/login');
  return user;
}

/**
 * For JSON API routes: require a logged-in user, or throw a 401 Response.
 */
export async function requireUserJson(request: Request): Promise<SessionUser> {
  const user = await getUser(request);
  if (!user) {
    throw new Response(JSON.stringify({ error: 'Not authenticated' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }
  return user;
}
