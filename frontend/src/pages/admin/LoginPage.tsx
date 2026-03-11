import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { authApi } from '../../api/adminApi';
import { useAuthStore } from '../../stores/authStore';
import { getApiErrorMessage, getApiErrorStatus } from '../../utils/errorMessage';
import {
  getAvailableSSOProviders,
  getSSOProviderInfo,
  initiateSSOLogin,
  type SSOProvider,
} from '../../utils/ssoAuth';
import { clearExplicitLogout, wasExplicitLogout } from '../../utils/tokenExpiry';


// SSO Provider Icons
function SSOProviderIcon({ provider }: { provider: SSOProvider }) {
  switch (provider) {
    case 'google':
      return (
        <svg className="w-5 h-5" viewBox="0 0 24 24">
          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
          <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg>
      );
    case 'microsoft':
      return (
        <svg className="w-5 h-5" viewBox="0 0 21 21">
          <rect x="1" y="1" width="9" height="9" fill="#f25022"/>
          <rect x="1" y="11" width="9" height="9" fill="#00a4ef"/>
          <rect x="11" y="1" width="9" height="9" fill="#7fba00"/>
          <rect x="11" y="11" width="9" height="9" fill="#ffb900"/>
        </svg>
      );
    case 'github':
      return (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
        </svg>
      );
    case 'keycloak':
      return (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
        </svg>
      );
    case 'hub':
      return (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
        </svg>
      );
    default:
      return (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
      );
  }
}


export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const login = useAuthStore((state) => state.login);
  const setToken = useAuthStore((state) => state.setToken);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [ssoProviders, setSsoProviders] = useState<SSOProvider[]>([]);
  const [ssoLoading, setSsoLoading] = useState<SSOProvider | null>(null);

  const ssoOnly = import.meta.env.VITE_SSO_ONLY === 'true';

  // Check for available SSO providers on mount
  useEffect(() => {
    const providers = getAvailableSSOProviders();
    setSsoProviders(providers);

    // Also query backend to detect Hub SSO at runtime (no rebuild needed)
    // If backend reports Hub configured, ensure 'hub' provider is present.
    (async () => {
      try {
        const res = await fetch('/auth/hub/check');
        if (res.ok) {
          const json = await res.json();
          if (json?.configured && !providers.includes('hub')) {
            setSsoProviders((prev) => Array.from(new Set([...prev, 'hub'])));
          }
        }
      } catch (e) {
        // ignore network errors — fall back to env-based providers
      }
    })();

    // Auto-redirect to Hub SSO if it's the only/primary provider
    // Skip if there's an error in URL (returning from failed SSO)
    const params = new URLSearchParams(location.search);
    const hasError = params.get('error');
    const skipAutoRedirect = params.get('manual') === 'true' || wasExplicitLogout();

    if (!hasError && !skipAutoRedirect && providers.includes('hub')) {
      // Auto-redirect to Hub SSO (if SSO-only mode or hub is primary)
      if (ssoOnly || providers.length === 1) {
        initiateSSOLogin('hub');
        return;
      }
    }
  }, []);

  // Check for redirect back from SSO with error
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const ssoError = params.get('error');
    if (ssoError) {
      setError(decodeURIComponent(ssoError));
    }
  }, [location]);

  const handleSSOLogin = (provider: SSOProvider) => {
    clearExplicitLogout();
    setSsoLoading(provider);
    initiateSSOLogin(provider);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Login and get token
      const tokenResponse = await authApi.login({
        username: email,
        password: password,
      });

      // Store token first so it's available for subsequent requests
      setToken(tokenResponse.access_token);

      // Get user info (now token is available in store)
      const userInfo = await authApi.getMe();

      // Check if user has admin access
      if (!userInfo.is_superuser && userInfo.role !== 'admin') {
        setError('Доступ запрещен. Требуются права администратора.');
        setLoading(false);
        return;
      }

      // Store auth data
      login(tokenResponse.access_token, userInfo, tokenResponse.refresh_token ?? undefined);

      // Redirect to admin dashboard
      navigate('/admin');
    } catch (err) {
      if (getApiErrorStatus(err) === 401) {
        setError('Неверный email или пароль');
      } else {
        setError(getApiErrorMessage(err, 'Ошибка входа. Попробуйте позже.'));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#5F6062]">
      <div className="max-w-md w-full mx-4">
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center mb-4">
              <img src="/severin-logo.png" alt="Severin" className="w-16 h-16" />
            </div>
            <h1 className="text-2xl font-bold text-slate-800">Severin<span className="text-severin-red">Autoprotocol</span></h1>
            <p className="text-slate-500 mt-2">Вход в систему</p>
          </div>

          {/* Direct Hub SSO button (always available in production) */}
          {(ssoOnly || import.meta.env.PROD) && (
            <div className="mb-4">
              <a
                href="/auth/hub/login?redirect_to=/admin"
                className="w-full inline-block text-center py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition"
              >
                Войти через корпоративный SSO
              </a>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          )}

          {/* Login Form */}
          {!ssoOnly && (
            <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-2">
                Email или имя пользователя
              </label>
              <input
                id="email"
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-severin-red focus:border-transparent transition"
                placeholder="admin"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-2">
                Пароль
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-severin-red focus:border-transparent transition"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 bg-severin-red hover:bg-severin-red-dark disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-medium rounded-lg transition duration-200 flex items-center justify-center"
            >
              {loading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Вход...
                </>
              ) : (
                'Войти'
              )}
            </button>
            </form>
          )}

          {/* SSO Login Options */}
          {ssoProviders.length > 0 && (
            <>
              {/* Divider */}
              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-200"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white text-slate-400">или войти через</span>
                </div>
              </div>

              {/* SSO Buttons */}
              <div className="space-y-3">
                {ssoProviders.map((provider) => {
                  const info = getSSOProviderInfo(provider);
                  const isLoading = ssoLoading === provider;

                  return (
                    <button
                      key={provider}
                      onClick={() => handleSSOLogin(provider)}
                      disabled={!!ssoLoading}
                      className="w-full py-3 px-4 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 disabled:cursor-not-allowed text-slate-700 font-medium rounded-lg transition duration-200 flex items-center justify-center gap-3"
                      style={{ borderLeft: `4px solid ${info.color}` }}
                    >
                      {isLoading ? (
                        <svg className="animate-spin h-5 w-5 text-slate-600" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                      ) : (
                        <SSOProviderIcon provider={provider} />
                      )}
                      <span>Войти через {info.name}</span>
                    </button>
                  );
                })}
              </div>
            </>
          )}

          {/* Back link */}
          <div className="mt-6 text-center">
            <a href="/" className="text-sm text-slate-500 hover:text-severin-red transition">
              ← Вернуться к приложению
            </a>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-white/60 text-sm mt-8">
          SeverinAutoprotocol v2.0 · Design by <span className="text-red-400">N. Khromenok</span> & <span className="text-red-400">V. Vasin</span>
        </p>
      </div>
    </div>
  );
}
