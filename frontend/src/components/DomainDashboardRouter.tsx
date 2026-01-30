/**
 * Domain Dashboard Router
 *
 * Automatically routes to the appropriate dashboard based on user's active domain.
 * - construction -> ManagerDashboardPage (with projects)
 * - hr -> HRDashboardPage
 * - dct -> DCTDashboardPage (Департамент Цифровой Трансформации)
 */
import { useAuthStore } from '../stores/authStore';
import { ManagerDashboardPage } from '../pages/ManagerDashboardPage';
import { HRDashboardPage } from '../pages/HRDashboardPage';
import { DCTDashboardPage } from '../pages/DCTDashboardPage';

export function DomainDashboardRouter() {
  const { user } = useAuthStore();

  // Determine active domain
  const activeDomain = user?.active_domain || user?.domain || 'construction';

  // Render appropriate dashboard
  switch (activeDomain) {
    case 'hr':
      return <HRDashboardPage />;
    case 'dct':
      return <DCTDashboardPage />;
    case 'construction':
    default:
      return <ManagerDashboardPage />;
  }
}

export default DomainDashboardRouter;
