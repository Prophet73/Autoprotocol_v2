/**
 * SSO Authentication utilities.
 *
 * Supports multiple SSO providers:
 * - OAuth 2.0 / OpenID Connect
 * - SAML (via backend proxy)
 * - Custom enterprise SSO
 */

export type SSOProvider = 'google' | 'microsoft' | 'github' | 'keycloak' | 'hub' | 'custom';

interface SSOConfig {
  provider: SSOProvider;
  clientId: string;
  authUrl: string;
  redirectUri: string;
  scope: string;
  responseType: string;
}

// SSO configurations (loaded from env or backend)
const SSO_CONFIGS: Record<string, Partial<SSOConfig>> = {
  google: {
    provider: 'google',
    authUrl: 'https://accounts.google.com/o/oauth2/v2/auth',
    scope: 'openid email profile',
    responseType: 'code',
  },
  microsoft: {
    provider: 'microsoft',
    authUrl: 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
    scope: 'openid email profile',
    responseType: 'code',
  },
  github: {
    provider: 'github',
    authUrl: 'https://github.com/login/oauth/authorize',
    scope: 'read:user user:email',
    responseType: 'code',
  },
  keycloak: {
    provider: 'keycloak',
    // authUrl configured per deployment
    scope: 'openid email profile',
    responseType: 'code',
  },
  hub: {
    provider: 'hub',
    // Uses backend redirect, no direct OAuth
    scope: 'openid email profile',
    responseType: 'code',
  },
};

/**
 * Get available SSO providers from environment
 */
export function getAvailableSSOProviders(): SSOProvider[] {
  const providers: SSOProvider[] = [];

  if (import.meta.env.VITE_SSO_GOOGLE_CLIENT_ID) {
    providers.push('google');
  }
  if (import.meta.env.VITE_SSO_MICROSOFT_CLIENT_ID) {
    providers.push('microsoft');
  }
  if (import.meta.env.VITE_SSO_GITHUB_CLIENT_ID) {
    providers.push('github');
  }
  if (import.meta.env.VITE_SSO_KEYCLOAK_URL) {
    providers.push('keycloak');
  }
  if (import.meta.env.VITE_SSO_CUSTOM_URL) {
    providers.push('custom');
  }
  if (import.meta.env.VITE_SSO_HUB_ENABLED === 'true') {
    providers.push('hub');
  }

  return providers;
}

/**
 * Generate state parameter for CSRF protection
 */
function generateState(): string {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  const state = Array.from(array, (byte) => byte.toString(16).padStart(2, '0')).join('');
  sessionStorage.setItem('sso_state', state);
  return state;
}

/**
 * Verify state parameter on callback
 */
export function verifyState(state: string): boolean {
  const savedState = sessionStorage.getItem('sso_state');
  sessionStorage.removeItem('sso_state');
  return savedState === state;
}

/**
 * Build OAuth authorization URL
 */
export function buildSSOAuthUrl(provider: SSOProvider): string {
  const baseConfig = SSO_CONFIGS[provider];
  if (!baseConfig) {
    throw new Error(`Unknown SSO provider: ${provider}`);
  }

  const redirectUri = `${window.location.origin}/auth/callback`;
  const state = generateState();

  let clientId: string;
  let authUrl: string;

  switch (provider) {
    case 'google':
      clientId = import.meta.env.VITE_SSO_GOOGLE_CLIENT_ID || '';
      authUrl = baseConfig.authUrl!;
      break;
    case 'microsoft':
      clientId = import.meta.env.VITE_SSO_MICROSOFT_CLIENT_ID || '';
      authUrl = baseConfig.authUrl!;
      break;
    case 'github':
      clientId = import.meta.env.VITE_SSO_GITHUB_CLIENT_ID || '';
      authUrl = baseConfig.authUrl!;
      break;
    case 'keycloak':
      clientId = import.meta.env.VITE_SSO_KEYCLOAK_CLIENT_ID || '';
      authUrl = `${import.meta.env.VITE_SSO_KEYCLOAK_URL}/protocol/openid-connect/auth`;
      break;
    case 'custom':
      clientId = import.meta.env.VITE_SSO_CUSTOM_CLIENT_ID || '';
      authUrl = import.meta.env.VITE_SSO_CUSTOM_URL || '';
      break;
    default:
      throw new Error(`Unsupported SSO provider: ${provider}`);
  }

  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: baseConfig.responseType || 'code',
    scope: baseConfig.scope || 'openid email profile',
    state,
  });

  // Add nonce for OpenID Connect
  if (baseConfig.scope?.includes('openid')) {
    const nonce = crypto.randomUUID();
    sessionStorage.setItem('sso_nonce', nonce);
    params.append('nonce', nonce);
  }

  return `${authUrl}?${params.toString()}`;
}

/**
 * Initiate SSO login flow
 */
export function initiateSSOLogin(provider: SSOProvider): void {
  // Hub uses backend redirect flow
  if (provider === 'hub') {
    sessionStorage.setItem('sso_provider', provider);
    window.location.href = '/auth/hub/login?redirect_to=/admin';
    return;
  }

  const authUrl = buildSSOAuthUrl(provider);
  // Store provider for callback
  sessionStorage.setItem('sso_provider', provider);
  // Redirect to SSO provider
  window.location.href = authUrl;
}

/**
 * Handle SSO callback - exchange code for token via backend
 */
export async function handleSSOCallback(
  code: string,
  state: string,
  provider: SSOProvider
): Promise<{ token: string; user: unknown }> {
  // Verify state
  if (!verifyState(state)) {
    throw new Error('Invalid state parameter - possible CSRF attack');
  }

  // Exchange code for token via backend
  const response = await fetch('/api/auth/sso/callback', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      provider,
      code,
      redirect_uri: `${window.location.origin}/auth/callback`,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'SSO authentication failed');
  }

  return response.json();
}

/**
 * Get SSO provider display info
 */
export function getSSOProviderInfo(provider: SSOProvider): {
  name: string;
  icon: string;
  color: string;
} {
  switch (provider) {
    case 'google':
      return { name: 'Google', icon: 'google', color: '#4285F4' };
    case 'microsoft':
      return { name: 'Microsoft', icon: 'microsoft', color: '#00A4EF' };
    case 'github':
      return { name: 'GitHub', icon: 'github', color: '#333' };
    case 'keycloak':
      return { name: 'Keycloak', icon: 'key', color: '#4D4D4D' };
    case 'hub':
      return { name: 'Corporate SSO', icon: 'building', color: '#3B82F6' };
    case 'custom':
      return { name: 'SSO', icon: 'lock', color: '#6366F1' };
    default:
      return { name: 'SSO', icon: 'lock', color: '#6366F1' };
  }
}
