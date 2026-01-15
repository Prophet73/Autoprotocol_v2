import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { DashboardLayout } from './components/DashboardLayout';
import { UploadPage } from './pages/UploadPage';
import { JobPage } from './pages/JobPage';
import { HistoryPage } from './pages/HistoryPage';
import { ManagerDashboardPage } from './pages/ManagerDashboardPage';
import { HRDashboardPage } from './pages/HRDashboardPage';
import { ITDashboardPage } from './pages/ITDashboardPage';
import { DomainDashboardRouter } from './components/DomainDashboardRouter';

// Admin imports
import LoginPage from './pages/admin/LoginPage';
import AdminLayout from './components/admin/AdminLayout';
import AuthGuard from './components/admin/AuthGuard';
import DashboardPage from './pages/admin/DashboardPage';
import UsersPage from './pages/admin/UsersPage';
import SettingsPage from './pages/admin/SettingsPage';
import ProjectsPage from './pages/admin/ProjectsPage';
import LogsPage from './pages/admin/LogsPage';
import StatsPage from './pages/admin/StatsPage';
import JobsPage from './pages/admin/JobsPage';
import SSOCallbackPage from './pages/SSOCallbackPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5000,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
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
          <Route
            path="/dashboard"
            element={
              <AuthGuard requiredRole="manager">
                <DashboardLayout>
                  <DomainDashboardRouter />
                </DashboardLayout>
              </AuthGuard>
            }
          />

          {/* Direct dashboard routes for each domain */}
          <Route
            path="/dashboard/construction"
            element={
              <AuthGuard requiredRole="manager">
                <DashboardLayout>
                  <ManagerDashboardPage />
                </DashboardLayout>
              </AuthGuard>
            }
          />
          <Route
            path="/dashboard/hr"
            element={
              <AuthGuard requiredRole="manager">
                <Layout>
                  <HRDashboardPage />
                </Layout>
              </AuthGuard>
            }
          />
          <Route
            path="/dashboard/it"
            element={
              <AuthGuard requiredRole="manager">
                <Layout>
                  <ITDashboardPage />
                </Layout>
              </AuthGuard>
            }
          />

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
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
