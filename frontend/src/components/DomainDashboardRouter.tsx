/**
 * Domain Dashboard Router
 *
 * Automatically routes to the appropriate dashboard based on user's active domain.
 * Dashboard components are resolved from the unified domain registry.
 */
import { Suspense } from 'react';
import { useAuthStore } from '../stores/authStore';
import { getDomainConfig, DOMAIN_REGISTRY } from '../config/domains';

export function DomainDashboardRouter() {
  const { user } = useAuthStore();

  const activeDomain = user?.active_domain || user?.domain || 'construction';

  const fallback = (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-severin-red" />
    </div>
  );

  // Resolve dashboard from registry, fallback to first registered domain
  const config = getDomainConfig(activeDomain) ?? DOMAIN_REGISTRY[0];
  const Dashboard = config.dashboard;

  return (
    <Suspense fallback={fallback}>
      <Dashboard />
    </Suspense>
  );
}

export default DomainDashboardRouter;
