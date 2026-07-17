import { proxyAgentRequest } from '../lib/agent-proxy.server';
import { requireUserJson } from '../lib/auth.server';

// Suggestion dispositions (accepted/dismissed/snoozed/saved) relay through the
// Agent to Navi — the learning half of the suggestions loop. Body:
// { id: string, disposition: string }.
export async function action({ request }: { request: Request }) {
  const user = await requireUserJson(request);
  const body = (await request.json().catch(() => ({}))) as {
    id?: string;
    disposition?: string;
  };
  if (!body.id || !body.disposition) {
    return Response.json({ error: 'id and disposition are required' }, { status: 400 });
  }
  return proxyAgentRequest({
    user,
    path: `/suggestions/${encodeURIComponent(body.id)}/feedback`,
    method: 'POST',
    body: { disposition: body.disposition },
  });
}
