import { handleGoogleCallback } from '../lib/auth.server';

export async function loader({ request }: { request: Request }) {
  return handleGoogleCallback(request);
}
