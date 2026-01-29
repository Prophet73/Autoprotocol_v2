import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Building2, Sparkles, LogOut } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

/**
 * Full-screen layout for Dashboard with top bar like admin.
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
      {/* Top bar */}
      <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-4 flex-shrink-0 z-50">
        {/* Left: Back + Logo + Title */}
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="flex items-center gap-2 text-slate-500 hover:text-severin-red transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            <span className="text-sm hidden sm:inline">Назад</span>
          </Link>
          <div className="w-px h-6 bg-slate-200" />
          <div className="flex items-center gap-2.5">
            <img src="/severin-logo.png" alt="Autoprotocol" className="w-7 h-7" />
            <span className="text-lg font-bold text-slate-800">Autoprotocol</span>
          </div>
          <div className="w-px h-5 bg-slate-200 hidden sm:block" />
          <span className="text-sm text-slate-500 hidden sm:inline">Дашборд</span>
        </div>

        {/* Right: External links + User + Logout */}
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
          {user && (
            <>
              <div className="w-px h-5 bg-slate-200" />
              <span className="text-slate-600 hidden sm:inline">{user.full_name || user.email}</span>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-slate-500 hover:bg-red-50 hover:text-red-600 transition-all"
                title="Выйти"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Выйти</span>
              </button>
            </>
          )}
        </div>
      </header>

      {/* Main content - full width, full height */}
      <main className="flex-1 overflow-hidden bg-slate-50">
        {children}
      </main>
    </div>
  );
}
