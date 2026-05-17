/**
 * Server-side helper to forward authenticated requests from the UI to the Agent.
 *
 * Browser-side fetches can't carry INTERNAL_AUTH_SECRET (it lives in
 * server env only), so any Agent call originating from a React component
 * has to be proxied through a UI route that:
 *   1. Validates the user's session cookie via requireUserJson
 *   2. Re-issues the request to the Agent with the matching auth headers
 */

import { buildAgentAuthHeaders } from './agent-auth.server';
import type { SessionUser } from './session.server';

const AGENT_URL = process.env.VITE_AI_AGENT_API_URL || 'http://localhost:8001';

const COMMON_HEADERS = {
  'Content-Type': 'application/json',
  'API-Version': 'v1',
};

type ProxyOptions = {
  user: SessionUser;
  path: string;
  method?: 'GET' | 'POST';
  body?: unknown;
};

export async function proxyAgentRequest({
  user,
  path,
  method = 'GET',
  body,
}: ProxyOptions): Promise<Response> {
  try {
    const init: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...buildAgentAuthHeaders(user.email),
      },
    };
    if (body !== undefined && method !== 'GET') {
      init.body = JSON.stringify(body);
    }

    const resp = await fetch(`${AGENT_URL}${path}`, init);
    const text = await resp.text();

    return new Response(text, {
      status: resp.status,
      headers: COMMON_HEADERS,
    });
  } catch (error) {
    console.error(`Agent proxy error (${method} ${path}):`, error);
    return new Response(
      JSON.stringify({
        error: 'Agent service unavailable',
        timestamp: new Date().toISOString(),
      }),
      { status: 502, headers: COMMON_HEADERS }
    );
  }
}
