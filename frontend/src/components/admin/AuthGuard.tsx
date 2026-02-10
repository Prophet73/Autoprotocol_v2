import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';

type RequiredRole = 'admin' | 'manager' | 'viewer' | 'user';

interface AuthGuardProps {
  children: React.ReactNode;
  requiredRole?: RequiredRole;
}

export default function AuthGuard({ children, requiredRole = 'admin' }: AuthGuardProps) {
  const { isAuthenticated, user } = useAuthStore();
  const location = useLocation();

  // Debug
  console.log('AuthGuard:', { isAuthenticated, user, requiredRole, role: user?.role, is_superuser: user?.is_superuser });

  // Check if user is authenticated
  if (!isAuthenticated) {
    // If not authenticated, redirect user directly to Hub SSO login
    // preserving the original destination so Hub can redirect back
    const redirectTo = encodeURIComponent(location.pathname + (location.search || ''));
    return <Navigate to={`/auth/hub/login?redirect_to=${redirectTo}`} replace />;
  }

  // Check role-based access
  // Hierarchy: superuser > admin > manager > viewer > user
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

      case 'viewer':
        // Viewers, managers, admins, and superusers
        return ['viewer', 'manager', 'admin', 'superuser'].includes(user?.role || '');

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
