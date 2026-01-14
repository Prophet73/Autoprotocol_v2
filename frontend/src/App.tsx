import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { DashboardLayout } from './components/DashboardLayout';
import { UploadPage } from './pages/UploadPage';
import { JobPage } from './pages/JobPage';
import { HistoryPage } from './pages/HistoryPage';
import { ManagerDashboardPage } from './pages/ManagerDashboardPage';

// Admin imports
import LoginPage from './pages/admin/LoginPage';
import AdminLayout from './components/admin/AdminLayout';
import AuthGuard from './components/admin/AuthGuard';
import DashboardPage from './pages/admin/DashboardPage';
import UsersPage from './pages/admin/UsersPage';
import SettingsPage from './pages/admin/SettingsPage';
import ProjectsPage from './pages/admin/ProjectsPage';
import LogsPage from './pages/admin/LogsPage';
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

          {/* Manager dashboard (requires manager role) - full-width layout */}
          <Route
            path="/dashboard"
            element={
              <AuthGuard requiredRole="manager">
                <DashboardLayout>
                  <ManagerDashboardPage />
                </DashboardLayout>
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
