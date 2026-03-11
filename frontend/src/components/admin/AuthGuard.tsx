import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { isTokenExpired, triggerSSOReauth, wasExplicitLogout } from '../../utils/tokenExpiry';
import { Loader2 } from 'lucide-react';

type RequiredRole = 'admin' | 'manager' | 'viewer' | 'user';

interface AuthGuardProps {
  children: React.ReactNode;
  requiredRole?: RequiredRole;
}

export default function AuthGuard({ children, requiredRole = 'admin' }: AuthGuardProps) {
  const { isAuthenticated, token, user, logout } = useAuthStore();
  const location = useLocation();
  const hubEnabled = import.meta.env.VITE_SSO_HUB_ENABLED === 'true';

  // Not authenticated at all
  if (!isAuthenticated || !token) {
    if (hubEnabled && !wasExplicitLogout()) {
      const redirectTo = encodeURIComponent(location.pathname + (location.search || ''));
      window.location.href = `/auth/hub/login?redirect_to=${redirectTo}`;
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <Loader2 className="w-10 h-10 text-blue-600 animate-spin mx-auto mb-3" />
            <p className="text-gray-500">Перенаправление на авторизацию...</p>
          </div>
        </div>
      );
    }
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Token expired (stale tab / long idle) — proactively re-auth via SSO
  if (isTokenExpired(token)) {
    logout();
    if (hubEnabled) {
      triggerSSOReauth(location.pathname + (location.search || ''));
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <Loader2 className="w-10 h-10 text-blue-600 animate-spin mx-auto mb-3" />
            <p className="text-gray-500">Сессия истекла, обновление авторизации...</p>
          </div>
        </div>
      );
    }
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role-based access
  const hasAccess = (() => {
    if (user?.is_superuser) return true;

    switch (requiredRole) {
      case 'admin':
        return user?.role === 'admin' || user?.role === 'superuser';
      case 'manager':
        return ['manager', 'admin', 'superuser'].includes(user?.role || '');
      case 'viewer':
        return ['viewer', 'manager', 'admin', 'superuser'].includes(user?.role || '');
      case 'user':
        return true;
      default:
        return false;
    }
  })();

  if (!hasAccess) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
