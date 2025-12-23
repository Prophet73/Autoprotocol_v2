import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';

type RequiredRole = 'admin' | 'manager' | 'user';

interface AuthGuardProps {
  children: React.ReactNode;
  requiredRole?: RequiredRole;
}

export default function AuthGuard({ children, requiredRole = 'admin' }: AuthGuardProps) {
  const { isAuthenticated, user } = useAuthStore();
  const location = useLocation();

  // Check if user is authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role-based access
  const hasAccess = (() => {
    // Superusers have access to everything
    if (user?.is_superuser) return true;

    switch (requiredRole) {
      case 'admin':
        // Only admins and superusers
        return user?.role === 'admin' || user?.role === 'superuser';

      case 'manager':
        // Managers, admins, and superusers
        return ['manager', 'admin', 'superuser'].includes(user?.role || '');

      case 'user':
        // Any authenticated user
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
