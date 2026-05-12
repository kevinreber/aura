import { startGoogleOAuth } from '../lib/auth.server';

export async function loader({ request }: { request: Request }) {
  return startGoogleOAuth(request);
}
