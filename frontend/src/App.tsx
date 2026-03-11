import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { lazy, Suspense, useEffect } from 'react';
import { useAuthStore } from './stores/authStore';
import { isTokenExpired, triggerSSOReauth } from './utils/tokenExpiry';
import { Layout } from './components/Layout';
import { DashboardLayout } from './components/DashboardLayout';
import { UploadPage } from './pages/UploadPage';
import { JobPage } from './pages/JobPage';
import { HistoryPage } from './pages/HistoryPage';
import AuthGuard from './components/admin/AuthGuard';
import SSOCallbackPage from './pages/SSOCallbackPage';
import { DomainDashboardRouter } from './components/DomainDashboardRouter';
import { DOMAIN_REGISTRY } from './config/domains';

// Lazy-loaded admin pages
const LoginPage = lazy(() => import('./pages/admin/LoginPage'));
const AdminLayout = lazy(() => import('./components/admin/AdminLayout'));
const DashboardPage = lazy(() => import('./pages/admin/DashboardPage'));
const UsersPage = lazy(() => import('./pages/admin/UsersPage'));
const SettingsPage = lazy(() => import('./pages/admin/SettingsPage'));
const ProjectsPage = lazy(() => import('./pages/admin/ProjectsPage'));
const LogsPage = lazy(() => import('./pages/admin/LogsPage'));
const StatsPage = lazy(() => import('./pages/admin/StatsPage'));
const JobsPage = lazy(() => import('./pages/admin/JobsPage'));

function PageLoader() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-severin-red" />
    </div>
  );
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5000,
    },
  },
});

/**
 * When a stale tab becomes visible again, check if the JWT token has expired.
 * If so, proactively redirect to Hub SSO for silent re-auth —
 * the user gets a fresh token without seeing a login form (if Hub session is still alive).
 */
function useStaleTabReauth() {
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState !== 'visible') return;
      const { token, isAuthenticated, logout } = useAuthStore.getState();
      if (isAuthenticated && token && isTokenExpired(token)) {
        logout();
        if (import.meta.env.VITE_SSO_HUB_ENABLED === 'true') {
          triggerSSOReauth();
        } else {
          window.location.href = '/login';
        }
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, []);
}

function App() {
  useStaleTabReauth();

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={<PageLoader />}>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<Layout><UploadPage /></Layout>} />
          <Route path="/job/:jobId" element={<Layout><JobPage /></Layout>} />
          <Route path="/history" element={<Layout><HistoryPage /></Layout>} />

          {/* Admin login */}
          <Route path="/login" element={<LoginPage />} />

          {/* SSO callback */}
          <Route path="/auth/callback" element={<SSOCallbackPage />} />

          {/* Domain-aware dashboard - routes to appropriate dashboard based on user's domain */}
          {/* Accessible by viewer, manager, admin, superuser */}
          <Route
            path="/dashboard"
            element={
              <AuthGuard requiredRole="viewer">
                <DashboardLayout>
                  <DomainDashboardRouter />
                </DashboardLayout>
              </AuthGuard>
            }
          />

          {/* Direct dashboard routes for each domain — generated from registry */}
          {DOMAIN_REGISTRY.map(({ routePath, dashboard: Dashboard }) => (
            <Route
              key={routePath}
              path={`/dashboard/${routePath}`}
              element={
                <AuthGuard requiredRole="viewer">
                  <DashboardLayout>
                    <Dashboard />
                  </DashboardLayout>
                </AuthGuard>
              }
            />
          ))}

          {/* Protected admin routes */}
          <Route
            path="/admin"
            element={
              <AuthGuard>
                <AdminLayout />
              </AuthGuard>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="jobs" element={<JobsPage />} />
            <Route path="stats" element={<StatsPage />} />
            <Route path="users" element={<UsersPage />} />
            <Route path="projects" element={<ProjectsPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="logs" element={<LogsPage />} />
          </Route>

          {/* 404 catch-all */}
          <Route path="*" element={
            <Layout>
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <h1 className="text-4xl font-bold text-gray-900 mb-2">404</h1>
                <p className="text-gray-600 mb-6">Страница не найдена</p>
                <a href="/" className="text-severin-red hover:underline">На главную</a>
              </div>
            </Layout>
          } />
        </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
