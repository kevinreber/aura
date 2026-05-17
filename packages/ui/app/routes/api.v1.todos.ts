import { proxyAgentRequest } from '../lib/agent-proxy.server';
import { requireUserJson } from '../lib/auth.server';

export async function loader({ request }: { request: Request }) {
  const user = await requireUserJson(request);
  const url = new URL(request.url);
  const bucket = url.searchParams.get('bucket');
  const path = bucket ? `/tools/todos?bucket=${encodeURIComponent(bucket)}` : '/tools/todos';
  return proxyAgentRequest({ user, path, method: 'GET' });
}
