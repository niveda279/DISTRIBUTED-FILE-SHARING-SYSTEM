import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './context/AuthContext';
import Sidebar from './components/Sidebar';

import LandingPage          from './pages/LandingPage';
import LoginPage            from './pages/LoginPage';
import RegisterPage         from './pages/RegisterPage';
import Dashboard            from './pages/Dashboard';
import MyFilesPage          from './pages/MyFilesPage';
import SharedFilesPage      from './pages/SharedFilesPage';
import SearchPage           from './pages/SearchPage';
import NodesPage            from './pages/NodesPage';
import AdminDashboardPage   from './pages/AdminDashboardPage';
import ClusterTopologyPage  from './pages/ClusterTopologyPage';
import SelfHealingPage      from './pages/SelfHealingPage';
import SimulationPage       from './pages/SimulationPage';
import SecurityCenterPage   from './pages/SecurityCenterPage';
import StorageAnalyticsPage from './pages/StorageAnalyticsPage';
import FileDetailPage       from './pages/FileDetailPage';

// Layout with sidebar for authenticated pages
function AppLayout() {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="page-content">
        <Outlet />
      </div>
    </div>
  );
}

// Route guard: redirect to /login if not authenticated
function PrivateRoute({ adminOnly = false }) {
  const { user, loading } = useAuth();
  if (loading) return (
    <div className="loading-page">
      <div className="spinner" />
    </div>
  );
  if (!user) return <Navigate to="/login" replace />;
  if (adminOnly && user.role !== 'ADMIN') return <Navigate to="/dashboard" replace />;
  return <AppLayout />;
}

// Redirect logged-in users away from auth pages
function PublicRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) return <Navigate to="/dashboard" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public */}
          <Route path="/" element={<PublicRoute><LandingPage /></PublicRoute>} />
          <Route path="/login"    element={<PublicRoute><LoginPage /></PublicRoute>} />
          <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />

          {/* Authenticated */}
          <Route element={<PrivateRoute />}>
            <Route path="/dashboard"  element={<Dashboard />} />
            <Route path="/files"      element={<MyFilesPage />} />
            <Route path="/files/:id"  element={<FileDetailPage />} />
            <Route path="/shared"     element={<SharedFilesPage />} />
            <Route path="/search"     element={<SearchPage />} />
            <Route path="/nodes"      element={<NodesPage />} />
            <Route path="/cluster"    element={<ClusterTopologyPage />} />
          </Route>

          {/* Admin only */}
          <Route element={<PrivateRoute adminOnly />}>
            <Route path="/admin"                element={<AdminDashboardPage />} />
            <Route path="/admin/healing"        element={<SelfHealingPage />} />
            <Route path="/admin/simulation"     element={<SimulationPage />} />
            <Route path="/admin/security"       element={<SecurityCenterPage />} />
            <Route path="/admin/analytics"      element={<StorageAnalyticsPage />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>

      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'var(--clr-surface)',
            color: 'var(--clr-text)',
            border: '1px solid var(--clr-border)',
            fontSize: '13px',
          },
          success: { iconTheme: { primary: 'var(--clr-success)', secondary: '#fff' } },
          error:   { iconTheme: { primary: 'var(--clr-danger)',  secondary: '#fff' } },
        }}
      />
    </AuthProvider>
  );
}
