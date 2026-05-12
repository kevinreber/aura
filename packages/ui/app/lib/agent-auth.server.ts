/**
 * Headers the UI sends to the Agent to attest the verified user.
 *
 * The Agent verifies INTERNAL_AUTH_SECRET (shared secret) and additionally
 * re-checks the email against its own ALLOWED_EMAILS list. This is
 * defense-in-depth: even if the Agent port is exposed, no one can hit it
 * without the shared secret AND an allowlisted email.
 */

export function buildAgentAuthHeaders(userEmail: string): Record<string, string> {
  const secret = process.env.INTERNAL_AUTH_SECRET;
  if (!secret) {
    // In dev we still send the email so the Agent can log it, but the Agent
    // will reject the request unless INTERNAL_AUTH_SECRET is also unset there.
    console.warn('INTERNAL_AUTH_SECRET not set — Agent calls will fail if Agent requires it');
  }
  const headers: Record<string, string> = {
    'X-User-Email': userEmail,
  };
  if (secret) headers['X-Internal-Auth'] = secret;
  return headers;
}
