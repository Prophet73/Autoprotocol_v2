import { useState } from 'react';
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
import { ArrowLeft, LogOut, LayoutDashboard, ListTodo, BarChart3, Users, Building2, Settings, AlertTriangle, Menu, X, Sparkles } from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';
import clsx from 'clsx';

interface NavItem {
  name: string;
  path: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { name: 'Дашборд', path: '/admin', icon: <LayoutDashboard className="w-5 h-5" /> },
  { name: 'Очередь задач', path: '/admin/jobs', icon: <ListTodo className="w-5 h-5" /> },
  { name: 'Статистика', path: '/admin/stats', icon: <BarChart3 className="w-5 h-5" /> },
  { name: 'Пользователи', path: '/admin/users', icon: <Users className="w-5 h-5" /> },
  { name: 'Проекты', path: '/admin/projects', icon: <Building2 className="w-5 h-5" /> },
  { name: 'Настройки', path: '/admin/settings', icon: <Settings className="w-5 h-5" /> },
  { name: 'Логи ошибок', path: '/admin/logs', icon: <AlertTriangle className="w-5 h-5" /> },
];

export default function AdminLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path: string) => {
    if (path === '/admin') {
      return location.pathname === '/admin';
    }
    return location.pathname.startsWith(path);
  };

  const getUserInitials = () => {
    if (user?.full_name) {
      return user.full_name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
    }
    return user?.email?.[0]?.toUpperCase() || 'A';
  };

  return (
    <div className="h-screen flex flex-col bg-slate-100 overflow-hidden">
      {/* Top bar */}
      <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-4 flex-shrink-0 z-50">
        {/* Left: Back + Logo + Title */}
        <div className="flex items-center gap-4">
          {/* Mobile menu button */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-1.5 rounded-lg text-slate-500 hover:bg-slate-100"
          >
            <Menu className="w-5 h-5" />
          </button>

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
          <span className="text-sm text-slate-500 hidden sm:inline">Админ-панель</span>
        </div>

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

      <div className="flex-1 flex overflow-hidden">
        {/* Mobile sidebar backdrop */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/50 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Sidebar */}
        <aside
          className={clsx(
            'fixed lg:static inset-y-0 left-0 z-50 w-[300px] bg-white border-r border-slate-200 flex flex-col transform transition-transform duration-300 ease-in-out lg:translate-x-0',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full'
          )}
        >
          {/* Mobile header */}
          <div className="flex items-center justify-between h-14 px-4 border-b border-slate-200 lg:hidden">
            <span className="font-semibold text-slate-800">Меню</span>
            <button
              onClick={() => setSidebarOpen(false)}
              className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-3 space-y-1 overflow-auto">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
                className={clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium transition-all',
                  isActive(item.path)
                    ? 'bg-red-50 text-severin-red'
                    : 'text-slate-600 hover:bg-slate-100'
                )}
              >
                {item.icon}
                <span>{item.name}</span>
              </Link>
            ))}
          </nav>

          {/* User section */}
          <div className="p-3 border-t border-slate-100 bg-slate-50">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-slate-200 rounded-full flex items-center justify-center text-sm font-medium text-slate-600">
                {getUserInitials()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-slate-800 truncate">
                  {user?.full_name || user?.email}
                </div>
                <div className="text-xs text-slate-400">
                  {user?.is_superuser ? 'Суперадмин' : user?.role}
                </div>
              </div>
              <button
                onClick={handleLogout}
                className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-white transition-all"
                title="Выйти"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Footer */}
          <div className="px-4 py-2 text-[10px] text-slate-400 text-center border-t border-slate-100">
            <div>v2.0 · Design by N. Khromenok & V. Vasin</div>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 p-6 bg-slate-50 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
