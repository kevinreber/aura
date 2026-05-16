import { logout } from '../lib/auth.server';

/**
 * Logout is intentionally POST-only.
 *
 * A GET-accessible logout endpoint is vulnerable to drive-by logout via any
 * cross-origin `<img src=".../auth/logout">` — SameSite=Lax still allows the
 * session cookie to ride along on top-level GETs. Requiring a form POST
 * means an attacker would need to actually submit a form from their origin,
 * which the browser blocks without CSRF tokens for non-simple requests.
 */
export async function action({ request }: { request: Request }) {
  return logout(request);
}
