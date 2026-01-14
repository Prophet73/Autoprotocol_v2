import { Link, useNavigate } from 'react-router-dom';
import { LogOut, User, Settings, Grid3X3, Home } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

/**
 * Full-width layout for Manager Dashboard.
 * Minimal header, no max-width constraints.
 */
export function DashboardLayout({ children }: DashboardLayoutProps) {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="h-screen flex flex-col bg-slate-100 overflow-hidden">
      {/* Compact Header */}
      <header className="bg-white border-b border-slate-200 shadow-sm flex-shrink-0">
        <div className="px-4 h-12 flex items-center justify-between">
          {/* Left: Logo + Nav */}
          <div className="flex items-center gap-4">
            {/* Hub Apps */}
            <a
              href="https://ai-hub.svrd.ru/apps"
              className="p-1.5 rounded-lg text-slate-400 hover:text-severin-red hover:bg-red-50 transition-all"
              title="Все приложения"
            >
              <Grid3X3 className="w-4 h-4" />
            </a>

            {/* Logo */}
            <Link to="/" className="flex items-center gap-2">
              <img src="/severin-logo.png" alt="Severin" className="w-7 h-7" />
              <span className="text-base font-bold text-slate-800">
                Severin<span className="text-severin-red">Autoprotocol</span>
              </span>
            </Link>

            {/* Breadcrumb */}
            <div className="flex items-center gap-2 text-sm text-slate-500 ml-4">
              <Link to="/" className="hover:text-severin-red transition-colors">
                <Home className="w-4 h-4" />
              </Link>
              <span>/</span>
              <span className="font-medium text-slate-700">Дашборд менеджера</span>
            </div>
          </div>

          {/* Right: User menu */}
          <div className="flex items-center gap-3">
            {/* Admin link */}
            {(user?.role === 'admin' || user?.is_superuser) && (
              <Link
                to="/admin"
                className="p-1.5 rounded-lg text-slate-400 hover:text-severin-red hover:bg-red-50 transition-all"
                title="Админ-панель"
              >
                <Settings className="w-4 h-4" />
              </Link>
            )}

            {/* User */}
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <User className="w-4 h-4" />
              <span className="max-w-32 truncate">{user?.full_name || user?.email}</span>
            </div>

            {/* Logout */}
            <button
              onClick={handleLogout}
              className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-all"
              title="Выйти"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main content - full width, full height */}
      <main className="flex-1 overflow-hidden">
        {children}
      </main>
    </div>
  );
}
