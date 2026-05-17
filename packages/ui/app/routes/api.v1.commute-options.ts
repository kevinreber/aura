import { proxyAgentRequest } from '../lib/agent-proxy.server';
import { requireUserJson } from '../lib/auth.server';

export async function action({ request }: { request: Request }) {
  const user = await requireUserJson(request);
  const body = await request.json().catch(() => ({}));
  return proxyAgentRequest({
    user,
    path: '/tools/commute-options',
    method: 'POST',
    body,
  });
}
