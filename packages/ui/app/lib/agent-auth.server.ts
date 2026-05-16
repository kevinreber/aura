/**
 * Headers the UI sends to the Agent to attest the verified user.
 *
 * The Agent verifies INTERNAL_AUTH_SECRET (shared secret) and additionally
 * re-checks the email against its own ALLOWED_EMAILS list. This is
 * defense-in-depth: even if the Agent port is exposed, no one can hit it
 * without the shared secret AND an allowlisted email.
 */

const INTERNAL_AUTH_SECRET = process.env.INTERNAL_AUTH_SECRET;

// Warn once at module load instead of per-request — this fires on every
// outbound Agent call otherwise and floods dev logs.
if (!INTERNAL_AUTH_SECRET) {
  console.warn(
    'INTERNAL_AUTH_SECRET not set — Agent will reject calls if it requires it'
  );
}

export function buildAgentAuthHeaders(userEmail: string): Record<string, string> {
  const headers: Record<string, string> = { 'X-User-Email': userEmail };
  if (INTERNAL_AUTH_SECRET) headers['X-Internal-Auth'] = INTERNAL_AUTH_SECRET;
  return headers;
}
