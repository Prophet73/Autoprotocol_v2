import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Upload, History, Activity, LogIn, LogOut, LayoutDashboard, Wrench, HelpCircle, Building2, Sparkles, ChevronDown, Check } from 'lucide-react';
import clsx from 'clsx';
import { useState, useRef, useEffect } from 'react';
import { useAuthStore } from '../stores/authStore';
import { authApi } from '../api/adminApi';

interface LayoutProps {
  children: React.ReactNode;
}

// Domain configuration
const DOMAIN_CONFIG: Record<string, { label: string; shortLabel: string; color: string }> = {
  construction: { label: 'Строительство', shortLabel: 'Стройка', color: 'bg-amber-500' },
  hr: { label: 'HR / Кадры', shortLabel: 'HR', color: 'bg-purple-500' },
  it: { label: 'IT / Разработка', shortLabel: 'IT', color: 'bg-blue-500' },
  general: { label: 'Общий', shortLabel: 'Общий', color: 'bg-slate-500' },
};

export function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, user, logout, setUser } = useAuthStore();
  const [domainOpen, setDomainOpen] = useState(false);
  const [domainLoading, setDomainLoading] = useState(false);
  const domainRef = useRef<HTMLDivElement>(null);

  // Close domain dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (domainRef.current && !domainRef.current.contains(event.target as Node)) {
        setDomainOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  const isJobPage = location.pathname.startsWith('/job/');

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const getUserInitials = () => {
    if (user?.full_name) {
      return user.full_name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
    }
    return user?.email?.[0]?.toUpperCase() || 'U';
  };

  // Domain switching
  const availableDomains = user?.is_superuser ? ['construction', 'hr', 'it'] : (user?.domains || []);
  const activeDomain = user?.active_domain || user?.domain || availableDomains[0] || 'construction';
  const currentDomainConfig = DOMAIN_CONFIG[activeDomain] || DOMAIN_CONFIG.general;
  const canSwitchDomain = availableDomains.length > 1;

  const handleDomainChange = async (domain: string) => {
    if (domain === activeDomain || domainLoading) return;
    setDomainLoading(true);
    try {
      const updatedUser = await authApi.setActiveDomain(domain);
      setUser(updatedUser);
      setDomainOpen(false);
    } catch (error) {
      console.error('Failed to switch domain:', error);
    } finally {
      setDomainLoading(false);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-slate-100">
      {/* Top bar - Logo + Service name */}
      <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-4 flex-shrink-0 z-50">
        {/* Left: Logo + Name */}
        <Link to="/" className="flex items-center gap-2.5">
          <img src="/severin-logo.png" alt="Severin" className="w-8 h-8" />
          <span className="text-lg font-bold text-slate-800">Autoprotocol</span>
        </Link>

        {/* Right: External links */}
        <div className="flex items-center gap-3 text-sm">
          <a
            href="https://portal.svrd.ru"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition-all"
          >
            <Building2 className="w-4 h-4" />
            <span className="hidden sm:inline">Портал</span>
          </a>
          <a
            href="https://ai-hub.svrd.ru/apps"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition-all"
          >
            <Sparkles className="w-4 h-4" />
            <span className="hidden sm:inline">AI Hub</span>
          </a>
        </div>
      </header>

      {/* Content with sidebar */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <aside className="w-[300px] bg-white border-r border-slate-200 flex flex-col flex-shrink-0">
          {/* Domain Selector - only for authenticated users with multiple domains */}
          {isAuthenticated && canSwitchDomain && (
            <div className="p-3 border-b border-slate-100" ref={domainRef}>
              <div className="relative">
                <button
                  onClick={() => setDomainOpen(!domainOpen)}
                  disabled={domainLoading}
                  className={clsx(
                    'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border border-slate-200 hover:border-slate-300 transition-all text-left',
                    domainLoading && 'opacity-50'
                  )}
                >
                  <div className={clsx('w-2.5 h-2.5 rounded-full', currentDomainConfig.color)} />
                  <span className="flex-1 text-sm font-medium text-slate-700">{currentDomainConfig.label}</span>
                  <ChevronDown className={clsx('w-4 h-4 text-slate-400 transition-transform', domainOpen && 'rotate-180')} />
                </button>

                {domainOpen && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-lg shadow-lg z-50 overflow-hidden">
                    <div className="py-1">
                      {availableDomains.map((domain) => {
                        const config = DOMAIN_CONFIG[domain] || DOMAIN_CONFIG.general;
                        const isActiveDomain = domain === activeDomain;
                        return (
                          <button
                            key={domain}
                            onClick={() => handleDomainChange(domain)}
                            className={clsx(
                              'w-full flex items-center gap-3 px-3 py-2 text-sm transition-colors',
                              isActiveDomain ? 'bg-slate-50 text-slate-900' : 'text-slate-600 hover:bg-slate-50'
                            )}
                          >
                            <div className={clsx('w-2.5 h-2.5 rounded-full', config.color)} />
                            <span className="flex-1 text-left">{config.label}</span>
                            {isActiveDomain && <Check className="w-4 h-4 text-green-500" />}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Single domain badge */}
          {isAuthenticated && !canSwitchDomain && availableDomains.length === 1 && (
            <div className="p-3 border-b border-slate-100">
              <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-slate-50 text-sm">
                <div className={clsx('w-2.5 h-2.5 rounded-full', currentDomainConfig.color)} />
                <span className="font-medium text-slate-600">{currentDomainConfig.label}</span>
              </div>
            </div>
          )}

          {/* Navigation */}
          <nav className="flex-1 p-3 space-y-1 overflow-auto">
            <Link
              to="/"
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium transition-all',
                isActive('/') && !isJobPage ? 'bg-red-50 text-severin-red' : 'text-slate-600 hover:bg-slate-100'
              )}
            >
              <Upload className="w-5 h-5" />
              Загрузка
            </Link>
            <Link
              to="/history"
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium transition-all',
                isActive('/history') ? 'bg-red-50 text-severin-red' : 'text-slate-600 hover:bg-slate-100'
              )}
            >
              <History className="w-5 h-5" />
              История
            </Link>

            {isJobPage && (
              <div className="flex items-center gap-3 px-3 py-2.5 bg-amber-50 text-amber-700 rounded-lg font-medium">
                <Activity className="w-5 h-5 animate-pulse" />
                Обработка
              </div>
            )}

            {/* Analytics section - for users with dashboard access */}
            {isAuthenticated && (user?.role === 'manager' || user?.role === 'admin' || user?.is_superuser || user?.role === 'viewer') && (
              <>
                <div className="pt-4 pb-2">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-3">Аналитика</div>
                </div>
                <Link
                  to="/dashboard"
                  className={clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium transition-all',
                    isActive('/dashboard') ? 'bg-red-50 text-severin-red' : 'text-slate-600 hover:bg-slate-100'
                  )}
                >
                  <LayoutDashboard className="w-5 h-5" />
                  Дашборд
                </Link>
              </>
            )}

            {/* Admin section */}
            {isAuthenticated && (user?.role === 'admin' || user?.is_superuser) && (
              <>
                <div className="pt-4 pb-2">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-3">Администрирование</div>
                </div>
                <Link
                  to="/admin"
                  className={clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium transition-all',
                    isActive('/admin') ? 'bg-red-50 text-severin-red' : 'text-slate-600 hover:bg-slate-100'
                  )}
                >
                  <Wrench className="w-5 h-5" />
                  Админ-панель
                </Link>
              </>
            )}
          </nav>

          {/* Bottom section */}
          <div className="border-t border-slate-100">
            {/* Support - disabled */}
            <div className="px-3 py-2">
              <button
                disabled
                className="flex items-center gap-3 px-3 py-2 rounded-lg text-slate-400 cursor-not-allowed w-full text-sm"
                title="Скоро"
              >
                <HelpCircle className="w-5 h-5" />
                Поддержка
                <span className="ml-auto text-[10px] bg-slate-100 px-1.5 py-0.5 rounded">скоро</span>
              </button>
            </div>

            {/* User section */}
            <div className="p-3 border-t border-slate-100 bg-slate-50">
              {isAuthenticated ? (
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 bg-slate-200 rounded-full flex items-center justify-center text-sm font-medium text-slate-600">
                    {getUserInitials()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-slate-800 truncate">
                      {user?.full_name || user?.email}
                    </div>
                    <div className="text-xs text-slate-400">{user?.role}</div>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-white transition-all"
                    title="Выйти"
                  >
                    <LogOut className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <Link
                  to="/login"
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium bg-severin-red text-white hover:bg-red-700 transition-all w-full justify-center"
                >
                  <LogIn className="w-4 h-4" />
                  Войти
                </Link>
              )}
            </div>

            {/* Footer */}
            <div className="px-4 py-2 text-[10px] text-slate-400 text-center border-t border-slate-100">
              <div>v2.0 · Design by N. Khromenok & V. Vasin</div>
            </div>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 p-6 bg-slate-50 overflow-auto">
          <div className="max-w-5xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
