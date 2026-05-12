/**
 * UI proxy route for /weekend/preferences on the MCP server.
 *
 * GET → proxies to MCP server's /weekend/preferences (current values)
 * PUT → proxies to MCP server's /weekend/preferences (validated write)
 *
 * Server-to-server fetch avoids CORS issues, mirroring the api.v1.chat.ts
 * pattern.
 */

import { requireUserJson } from '../lib/auth.server';

const MCP_SERVER_URL = process.env.VITE_MCP_SERVER_URL || 'http://localhost:8000';

const COMMON_HEADERS = {
  'Content-Type': 'application/json',
  'API-Version': 'v1',
};

export async function loader({ request }: { request: Request }) {
  try {
    await requireUserJson(request);
  } catch (resp) {
    if (resp instanceof Response) return resp;
    throw resp;
  }
  try {
    const response = await fetch(`${MCP_SERVER_URL}/weekend/preferences`);

    if (!response.ok) {
      throw new Error(`MCP server returned ${response.status}`);
    }

    const prefs = await response.json();

    // Also fetch the categories catalog so the UI has both pieces in one call.
    const catRes = await fetch(`${MCP_SERVER_URL}/weekend/categories`);
    const catalog = catRes.ok ? await catRes.json() : { categories: [] };

    return new Response(
      JSON.stringify({ preferences: prefs, catalog: catalog.categories }),
      { status: 200, headers: COMMON_HEADERS }
    );
  } catch (error) {
    console.error('Preferences GET proxy error:', error);
    return new Response(
      JSON.stringify({
        error: 'Could not load preferences from MCP server',
        timestamp: new Date().toISOString(),
      }),
      { status: 500, headers: COMMON_HEADERS }
    );
  }
}

export async function action({ request }: { request: Request }) {
  try {
    await requireUserJson(request);
  } catch (resp) {
    if (resp instanceof Response) return resp;
    throw resp;
  }
  if (request.method !== 'PUT') {
    return new Response(
      JSON.stringify({ error: 'Method not allowed — use PUT to update' }),
      { status: 405, headers: COMMON_HEADERS }
    );
  }

  try {
    const body = await request.json();

    const response = await fetch(`${MCP_SERVER_URL}/weekend/preferences`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const data = await response.json();

    if (!response.ok) {
      return new Response(
        JSON.stringify({
          error: data.detail || `MCP server returned ${response.status}`,
        }),
        { status: response.status, headers: COMMON_HEADERS }
      );
    }

    return new Response(JSON.stringify(data), {
      status: 200,
      headers: COMMON_HEADERS,
    });
  } catch (error) {
    console.error('Preferences PUT proxy error:', error);
    return new Response(
      JSON.stringify({
        error: 'Could not save preferences to MCP server',
        timestamp: new Date().toISOString(),
      }),
      { status: 500, headers: COMMON_HEADERS }
    );
  }
}
