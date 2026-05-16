import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  getUser,
  handleGoogleCallback,
  isEmailAllowed,
  logout,
  requireUser,
  requireUserJson,
  startGoogleOAuth,
} from './auth.server';
import { commitSession, getSession } from './session.server';

function mintCookie(set: (session: Awaited<ReturnType<typeof getSession>>) => void) {
  return async () => {
    const session = await getSession(null);
    set(session);
    return commitSession(session);
  };
}

describe('isEmailAllowed', () => {
  afterEach(() => vi.unstubAllEnvs());

  it('returns false when allowlist is empty', () => {
    vi.stubEnv('ALLOWED_EMAILS', '');
    expect(isEmailAllowed('kevin@example.com')).toBe(false);
  });

  it('returns false when allowlist is unset', () => {
    vi.stubEnv('ALLOWED_EMAILS', undefined);
    expect(isEmailAllowed('kevin@example.com')).toBe(false);
  });

  it('returns true for a listed email', () => {
    vi.stubEnv('ALLOWED_EMAILS', 'kevin@example.com,other@example.com');
    expect(isEmailAllowed('kevin@example.com')).toBe(true);
    expect(isEmailAllowed('other@example.com')).toBe(true);
  });

  it('returns false for an unlisted email', () => {
    vi.stubEnv('ALLOWED_EMAILS', 'kevin@example.com');
    expect(isEmailAllowed('intruder@example.com')).toBe(false);
  });

  it('is case-insensitive on both sides', () => {
    vi.stubEnv('ALLOWED_EMAILS', 'Kevin@Example.COM');
    expect(isEmailAllowed('KEVIN@example.com')).toBe(true);
  });

  it('tolerates whitespace and empty entries in the allowlist', () => {
    vi.stubEnv('ALLOWED_EMAILS', '  a@x.com , , b@x.com ,');
    expect(isEmailAllowed('a@x.com')).toBe(true);
    expect(isEmailAllowed('b@x.com')).toBe(true);
  });
});

describe('getUser', () => {
  afterEach(() => vi.unstubAllEnvs());

  it('returns null when there is no session cookie', async () => {
    const req = new Request('http://localhost/');
    expect(await getUser(req)).toBeNull();
  });

  it('returns null when session has no user', async () => {
    vi.stubEnv('ALLOWED_EMAILS', 'kevin@example.com');
    const cookie = await mintCookie((s) => s.set('oauthState', 'abc'))();
    const req = new Request('http://localhost/', { headers: { Cookie: cookie } });
    expect(await getUser(req)).toBeNull();
  });

  it('returns the user when session user is allowlisted', async () => {
    vi.stubEnv('ALLOWED_EMAILS', 'kevin@example.com');
    const cookie = await mintCookie((s) =>
      s.set('user', { email: 'kevin@example.com', name: 'Kevin' })
    )();
    const req = new Request('http://localhost/', { headers: { Cookie: cookie } });
    const user = await getUser(req);
    expect(user).toEqual({ email: 'kevin@example.com', name: 'Kevin' });
  });

  it('returns null when session user is no longer allowlisted', async () => {
    // Mint with one allowlist, then narrow it — the per-request recheck should kick.
    vi.stubEnv('ALLOWED_EMAILS', 'kevin@example.com');
    const cookie = await mintCookie((s) =>
      s.set('user', { email: 'kevin@example.com', name: 'Kevin' })
    )();
    vi.stubEnv('ALLOWED_EMAILS', 'someone-else@example.com');
    const req = new Request('http://localhost/', { headers: { Cookie: cookie } });
    expect(await getUser(req)).toBeNull();
  });
});

describe('requireUser', () => {
  afterEach(() => vi.unstubAllEnvs());

  it('throws a redirect Response to /login when no user', async () => {
    const req = new Request('http://localhost/dashboard');
    await expect(requireUser(req)).rejects.toMatchObject({
      status: 302,
      headers: expect.any(Headers),
    });
    const resp = await requireUser(req).catch((r) => r);
    expect(resp).toBeInstanceOf(Response);
    expect(resp.headers.get('Location')).toBe('/login');
  });

  it('returns the user when authenticated', async () => {
    vi.stubEnv('ALLOWED_EMAILS', 'kevin@example.com');
    const cookie = await mintCookie((s) =>
      s.set('user', { email: 'kevin@example.com', name: 'Kevin' })
    )();
    const req = new Request('http://localhost/', { headers: { Cookie: cookie } });
    const user = await requireUser(req);
    expect(user.email).toBe('kevin@example.com');
  });
});

describe('requireUserJson', () => {
  afterEach(() => vi.unstubAllEnvs());

  it('throws a 401 JSON Response when no user', async () => {
    const req = new Request('http://localhost/api/v1/chat');
    const thrown = await requireUserJson(req).catch((r) => r);
    expect(thrown).toBeInstanceOf(Response);
    expect(thrown.status).toBe(401);
    expect(thrown.headers.get('Content-Type')).toBe('application/json');
    expect(await thrown.json()).toEqual({ error: 'Not authenticated' });
  });

  it('returns the user when authenticated', async () => {
    vi.stubEnv('ALLOWED_EMAILS', 'kevin@example.com');
    const cookie = await mintCookie((s) =>
      s.set('user', { email: 'kevin@example.com', name: 'Kevin' })
    )();
    const req = new Request('http://localhost/api/v1/chat', { headers: { Cookie: cookie } });
    const user = await requireUserJson(req);
    expect(user.email).toBe('kevin@example.com');
  });
});

describe('startGoogleOAuth', () => {
  afterEach(() => vi.unstubAllEnvs());

  it('builds a Google consent URL with the expected params', async () => {
    vi.stubEnv('GOOGLE_CLIENT_ID', 'fake-client-id');
    vi.stubEnv('NODE_ENV', 'development');
    const req = new Request('http://localhost:5173/auth/google');
    const resp = await startGoogleOAuth(req);
    expect(resp.status).toBe(302);
    const loc = resp.headers.get('Location') || '';
    expect(loc).toMatch(/^https:\/\/accounts\.google\.com\/o\/oauth2\/v2\/auth\?/);
    const params = new URLSearchParams(loc.split('?')[1]);
    expect(params.get('client_id')).toBe('fake-client-id');
    expect(params.get('scope')).toBe('openid email profile');
    expect(params.get('response_type')).toBe('code');
    expect(params.get('prompt')).toBe('select_account');
    expect(params.get('redirect_uri')).toBe('http://localhost:5173/auth/google/callback');
    expect(params.get('state')).toMatch(/^[0-9a-f-]{36}$/);
    expect(resp.headers.get('Set-Cookie')).toMatch(/aura_session=/);
  });

  it('honors GOOGLE_REDIRECT_URI override', async () => {
    vi.stubEnv('GOOGLE_CLIENT_ID', 'fake-client-id');
    vi.stubEnv('GOOGLE_REDIRECT_URI', 'https://aura.example.com/auth/google/callback');
    vi.stubEnv('NODE_ENV', 'development');
    const req = new Request('http://localhost:5173/auth/google');
    const resp = await startGoogleOAuth(req);
    const params = new URLSearchParams((resp.headers.get('Location') || '').split('?')[1]);
    expect(params.get('redirect_uri')).toBe('https://aura.example.com/auth/google/callback');
  });

  it('throws in production when GOOGLE_REDIRECT_URI is unset', async () => {
    vi.stubEnv('GOOGLE_CLIENT_ID', 'fake-client-id');
    vi.stubEnv('GOOGLE_REDIRECT_URI', undefined);
    vi.stubEnv('NODE_ENV', 'production');
    const req = new Request('https://internal-host/auth/google');
    await expect(startGoogleOAuth(req)).rejects.toThrow(/GOOGLE_REDIRECT_URI must be set/);
  });

  it('throws when GOOGLE_CLIENT_ID is missing', async () => {
    vi.stubEnv('GOOGLE_CLIENT_ID', undefined);
    const req = new Request('http://localhost:5173/auth/google');
    await expect(startGoogleOAuth(req)).rejects.toThrow(/GOOGLE_CLIENT_ID/);
  });
});

describe('handleGoogleCallback', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('redirects to /login?error=invalid_state when state is missing', async () => {
    const req = new Request('http://localhost:5173/auth/google/callback?code=abc&state=xyz');
    const resp = await handleGoogleCallback(req);
    expect(resp.status).toBe(302);
    expect(resp.headers.get('Location')).toBe('/login?error=invalid_state');
    // Even on the error path, the cookie should be committed so any stale
    // oauthState is cleared.
    expect(resp.headers.get('Set-Cookie')).toMatch(/aura_session=/);
  });

  it('forwards Google error params back to /login', async () => {
    const req = new Request(
      'http://localhost:5173/auth/google/callback?error=access_denied'
    );
    const resp = await handleGoogleCallback(req);
    expect(resp.headers.get('Location')).toBe('/login?error=access_denied');
  });

  it('rejects users not in the allowlist and destroys the session', async () => {
    vi.stubEnv('GOOGLE_CLIENT_ID', 'fake-id');
    vi.stubEnv('GOOGLE_CLIENT_SECRET', 'fake-secret');
    vi.stubEnv('ALLOWED_EMAILS', 'kevin@example.com');
    vi.stubEnv('NODE_ENV', 'development');

    // Mint a cookie with a matching oauthState so we get past the state check.
    const cookie = await mintCookie((s) => s.set('oauthState', 'st-1'))();

    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access_token: 'tok' }),
    } as unknown as Response);
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        email: 'intruder@example.com',
        verified_email: true,
        name: 'Intruder',
      }),
    } as unknown as Response);

    const req = new Request(
      'http://localhost:5173/auth/google/callback?code=c&state=st-1',
      { headers: { Cookie: cookie } }
    );
    const resp = await handleGoogleCallback(req);
    expect(resp.headers.get('Location')).toBe('/login?error=not_authorized');
    // destroySession clears the cookie (Max-Age=0 / expires in the past).
    expect(resp.headers.get('Set-Cookie')).toMatch(/aura_session=/);
  });

  it('rejects unverified Google emails', async () => {
    vi.stubEnv('GOOGLE_CLIENT_ID', 'fake-id');
    vi.stubEnv('GOOGLE_CLIENT_SECRET', 'fake-secret');
    vi.stubEnv('ALLOWED_EMAILS', 'kevin@example.com');
    vi.stubEnv('NODE_ENV', 'development');

    const cookie = await mintCookie((s) => s.set('oauthState', 'st-2'))();
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access_token: 'tok' }),
    } as unknown as Response);
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        email: 'kevin@example.com',
        verified_email: false,
        name: 'Kevin',
      }),
    } as unknown as Response);

    const req = new Request(
      'http://localhost:5173/auth/google/callback?code=c&state=st-2',
      { headers: { Cookie: cookie } }
    );
    const resp = await handleGoogleCallback(req);
    expect(resp.headers.get('Location')).toBe('/login?error=unverified_email');
  });

  it('logs in an allowlisted, verified user and redirects to /', async () => {
    vi.stubEnv('GOOGLE_CLIENT_ID', 'fake-id');
    vi.stubEnv('GOOGLE_CLIENT_SECRET', 'fake-secret');
    vi.stubEnv('ALLOWED_EMAILS', 'kevin@example.com');
    vi.stubEnv('NODE_ENV', 'development');

    const cookie = await mintCookie((s) => s.set('oauthState', 'st-3'))();
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access_token: 'tok' }),
    } as unknown as Response);
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        email: 'kevin@example.com',
        verified_email: true,
        name: 'Kevin Reber',
        picture: 'https://example.com/pic.jpg',
      }),
    } as unknown as Response);

    const req = new Request(
      'http://localhost:5173/auth/google/callback?code=c&state=st-3',
      { headers: { Cookie: cookie } }
    );
    const resp = await handleGoogleCallback(req);
    expect(resp.status).toBe(302);
    expect(resp.headers.get('Location')).toBe('/');
    expect(resp.headers.get('Set-Cookie')).toMatch(/aura_session=/);

    // Round-trip the cookie back through getUser to confirm the session sticks.
    const sessionCookie = resp.headers.get('Set-Cookie')!.split(';')[0];
    const req2 = new Request('http://localhost:5173/', {
      headers: { Cookie: sessionCookie },
    });
    const user = await getUser(req2);
    expect(user).toEqual({
      email: 'kevin@example.com',
      name: 'Kevin Reber',
      picture: 'https://example.com/pic.jpg',
    });
  });
});

describe('logout', () => {
  it('clears the session cookie and redirects to /login', async () => {
    const cookie = await mintCookie((s) =>
      s.set('user', { email: 'kevin@example.com', name: 'Kevin' })
    )();
    const req = new Request('http://localhost:5173/auth/logout', {
      method: 'POST',
      headers: { Cookie: cookie },
    });
    const resp = await logout(req);
    expect(resp.status).toBe(302);
    expect(resp.headers.get('Location')).toBe('/login');
    expect(resp.headers.get('Set-Cookie')).toMatch(/aura_session=/);
  });
});
