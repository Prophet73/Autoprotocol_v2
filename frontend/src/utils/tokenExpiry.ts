/**
 * JWT token expiry utilities.
 *
 * Decodes the JWT payload (without verifying signature) to check expiration.
 * Used for proactive token refresh via SSO before API calls start failing with 401.
 */

/**
 * Get token expiration timestamp in milliseconds.
 * Returns null if token is invalid or has no exp claim.
 */
export function getTokenExpiryMs(token: string): number | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1]));
    return payload.exp ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

/**
 * Check if a JWT token is expired or will expire within `bufferMs` milliseconds.
 * Default buffer is 60 seconds — triggers re-auth slightly before actual expiry.
 */
export function isTokenExpired(token: string, bufferMs = 60_000): boolean {
  const exp = getTokenExpiryMs(token);
  if (!exp) return true;
  return Date.now() > exp - bufferMs;
}

/**
 * Mark that the user explicitly chose to log out (clicked "Выйти").
 * This prevents automatic SSO re-auth — the user stays on the login page.
 */
export function markExplicitLogout(): void {
  sessionStorage.setItem('explicit_logout', '1');
}

/**
 * Check if the last logout was explicit (user-initiated).
 */
export function wasExplicitLogout(): boolean {
  return sessionStorage.getItem('explicit_logout') === '1';
}

/**
 * Clear the explicit logout flag (called after successful SSO login).
 */
export function clearExplicitLogout(): void {
  sessionStorage.removeItem('explicit_logout');
}

/**
 * Redirect to Hub SSO for silent re-authentication.
 * If user still has an active Hub session, they get a new token seamlessly.
 * Skips re-auth if the user explicitly logged out.
 * Includes loop protection (30s cooldown).
 */
export function triggerSSOReauth(redirectPath?: string): void {
  // Don't auto-reauth if user explicitly logged out
  if (wasExplicitLogout()) {
    window.location.href = '/login?manual=true';
    return;
  }

  const lastAttempt = sessionStorage.getItem('sso_reauth_ts');
  const now = Date.now();

  if (lastAttempt && now - parseInt(lastAttempt) < 30_000) {
    // Already tried within 30 seconds — avoid redirect loop, go to login
    window.location.href = '/login?manual=true';
    return;
  }

  sessionStorage.setItem('sso_reauth_ts', now.toString());
  const currentPath = redirectPath ?? window.location.pathname + window.location.search;
  window.location.href = `/auth/hub/login?redirect_to=${encodeURIComponent(currentPath)}`;
}
