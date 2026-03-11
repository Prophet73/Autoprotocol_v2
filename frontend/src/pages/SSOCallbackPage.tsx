import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { verifyState, handleSSOCallback, type SSOProvider } from '../utils/ssoAuth';
import { useAuthStore, type User } from '../stores/authStore';
import { clearExplicitLogout } from '../utils/tokenExpiry';

export default function SSOCallbackPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const login = useAuthStore((state) => state.login);

  useEffect(() => {
    const processCallback = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const token = searchParams.get('token');  // Hub SSO direct token
      const rawRedirect = searchParams.get('redirect') || '/admin';
      // Prevent open redirect: only allow relative paths starting with /
      const redirect = rawRedirect.startsWith('/') && !rawRedirect.startsWith('//') ? rawRedirect : '/admin';
      const errorParam = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');

      // Handle OAuth error response
      if (errorParam) {
        sessionStorage.removeItem('sso_reauth_ts');
        setError(errorDescription || errorParam);
        return;
      }

      // Hub SSO: token is passed directly from backend
      if (token) {
        try {
          const refreshToken = searchParams.get('refresh');

          // Store token first
          const { setToken } = useAuthStore.getState();
          setToken(token);

          // Fetch user info with the token
          const response = await fetch('/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
          });

          if (!response.ok) {
            throw new Error('Failed to get user info');
          }

          const user = await response.json() as User;
          login(token, user, refreshToken ?? undefined);

          // Clear SSO re-auth guards so future token expirations can retry
          sessionStorage.removeItem('sso_reauth_ts');
          clearExplicitLogout();

          // Redirect to specified page
          navigate(redirect);
          return;
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Hub SSO authentication failed');
          return;
        }
      }

      // Standard OAuth flow: code + state
      if (!code || !state) {
        setError('Missing required parameters');
        return;
      }

      // Get provider from session storage
      const provider = sessionStorage.getItem('sso_provider') as SSOProvider | null;
      sessionStorage.removeItem('sso_provider');

      if (!provider) {
        setError('SSO provider not found');
        return;
      }

      // Verify state to prevent CSRF
      if (!verifyState(state)) {
        setError('Invalid state parameter - possible CSRF attack');
        return;
      }

      try {
        // Exchange code for token via backend
        const result = await handleSSOCallback(code, state, provider);

        // Cast user to proper type
        const user = result.user as User;

        // Store auth data
        login(result.token, user);

        // Redirect to dashboard or home based on role
        if (user?.is_superuser || user?.role === 'admin') {
          navigate('/admin');
        } else if (user?.role === 'manager') {
          navigate('/dashboard');
        } else {
          navigate('/');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'SSO authentication failed');
      }
    };

    processCallback();
  }, [searchParams, login, navigate]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full mx-4">
          <div className="bg-white rounded-lg shadow-lg p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h1 className="text-xl font-semibold text-gray-900 mb-2">Ошибка авторизации</h1>
            <p className="text-gray-600 mb-6">{error}</p>
            <button
              onClick={() => navigate('/login')}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              Попробовать снова
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
        <p className="text-gray-600">Завершение авторизации...</p>
      </div>
    </div>
  );
}
