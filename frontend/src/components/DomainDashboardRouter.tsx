/**
 * Domain Dashboard Router
 *
 * Automatically routes to the appropriate dashboard based on user's active domain.
 * - construction -> ManagerDashboardPage (with projects)
 * - hr -> HRDashboardPage
 * - it -> ITDashboardPage
 */
import { useAuthStore } from '../stores/authStore';
import { ManagerDashboardPage } from '../pages/ManagerDashboardPage';
import { HRDashboardPage } from '../pages/HRDashboardPage';
import { ITDashboardPage } from '../pages/ITDashboardPage';

export function DomainDashboardRouter() {
  const { user } = useAuthStore();

  // Determine active domain
  const activeDomain = user?.active_domain || user?.domain || 'construction';

  // Render appropriate dashboard
  switch (activeDomain) {
    case 'hr':
      return <HRDashboardPage />;
    case 'it':
      return <ITDashboardPage />;
    case 'construction':
    default:
      return <ManagerDashboardPage />;
  }
}

export default DomainDashboardRouter;
