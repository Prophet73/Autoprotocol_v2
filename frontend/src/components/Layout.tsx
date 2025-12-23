import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Mic2, Upload, History, Activity, LogIn, User, LogOut, LayoutDashboard, Settings } from 'lucide-react';
import clsx from 'clsx';
import { useAuthStore } from '../stores/authStore';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuthStore();

  const navItems = [
    { path: '/', label: 'Загрузка', icon: Upload },
    { path: '/history', label: 'История', icon: History },
  ];

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  // Check if we're on a job page
  const isJobPage = location.pathname.startsWith('/job/');

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-6xl mx-auto px-4">
          <div className="flex items-center justify-between h-14">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2 group">
              <div className="p-1.5 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-lg shadow-lg shadow-emerald-500/25 group-hover:shadow-emerald-500/40 transition-shadow">
                <Mic2 className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-slate-800">Severin<span className="text-emerald-600">Autoprotocol</span></h1>
              </div>
            </Link>

            {/* Navigation */}
            <nav className="flex items-center gap-1">
              {navItems.map(({ path, label, icon: Icon }) => (
                <Link
                  key={path}
                  to={path}
                  className={clsx(
                    'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
                    isActive(path)
                      ? 'bg-emerald-50 text-emerald-600'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </Link>
              ))}

              {/* Active job indicator */}
              {isJobPage && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 text-amber-700 rounded-lg text-sm font-medium ml-1">
                  <Activity className="w-4 h-4 animate-pulse" />
                  Обработка
                </div>
              )}

              {/* Auth section */}
              <div className="flex items-center gap-1 ml-3 pl-3 border-l border-slate-200">
                {isAuthenticated ? (
                  <>
                    {/* Dashboard link for managers */}
                    {(user?.role === 'manager' || user?.role === 'admin' || user?.is_superuser) && (
                      <Link
                        to="/dashboard"
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-all"
                      >
                        <LayoutDashboard className="w-4 h-4" />
                        Дашборд
                      </Link>
                    )}
                    {/* Admin link */}
                    {(user?.role === 'admin' || user?.is_superuser) && (
                      <Link
                        to="/admin"
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-all"
                      >
                        <Settings className="w-4 h-4" />
                      </Link>
                    )}
                    {/* User menu */}
                    <div className="flex items-center gap-2 px-3 py-1.5 text-sm text-slate-600">
                      <User className="w-4 h-4" />
                      <span className="max-w-24 truncate">{user?.full_name || user?.email}</span>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-sm text-slate-500 hover:bg-red-50 hover:text-red-600 transition-all"
                      title="Выйти"
                    >
                      <LogOut className="w-4 h-4" />
                    </button>
                  </>
                ) : (
                  <>
                    <Link
                      to="/login"
                      className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-all"
                    >
                      <LogIn className="w-4 h-4" />
                      Войти
                    </Link>
                  </>
                )}
              </div>
            </nav>
          </div>
        </div>
      </header>

      {/* Main content - flex-1 to push footer down */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-6">
        {children}
      </main>

      {/* Footer - always at bottom */}
      <footer className="border-t border-slate-200 bg-white/80 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <p>SeverinAutoprotocol v1.0</p>
            <div className="flex items-center gap-4">
              <a href="mailto:support@severin.ru" className="hover:text-slate-600 transition-colors">
                Поддержка
              </a>
              <a href="/docs" className="hover:text-slate-600 transition-colors">
                Документация
              </a>
              {!isAuthenticated && (
                <Link to="/admin" className="hover:text-slate-600 transition-colors">
                  Админ
                </Link>
              )}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
