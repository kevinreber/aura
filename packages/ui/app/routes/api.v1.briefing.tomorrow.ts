import { proxyAgentRequest } from '../lib/agent-proxy.server';
import { requireUserJson } from '../lib/auth.server';

export async function loader({ request }: { request: Request }) {
  const user = await requireUserJson(request);
  const url = new URL(request.url);
  const date = url.searchParams.get('date');
  const path = date
    ? `/briefing/tomorrow?date=${encodeURIComponent(date)}`
    : '/briefing/tomorrow';
  return proxyAgentRequest({ user, path, method: 'GET' });
}
