import { logout } from '../lib/auth.server';

export async function action({ request }: { request: Request }) {
  return logout(request);
}

export async function loader({ request }: { request: Request }) {
  // Allow GET for simple links/redirects too.
  return logout(request);
}
