import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom';
import { useAuthStore } from './features/auth/store';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { JobsPage } from './pages/JobsPage';
import { JobDetailsPage } from './pages/JobDetailsPage';

// Компонент-обертка: показывает менюшку только для авторизованных
const Layout = ({ children }: { children: React.ReactNode }) => {
  const logout = useAuthStore((state) => state.logout);
  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', padding: '16px 32px', backgroundColor: '#ffffff', borderBottom: '1px solid #e5e7eb' }}>
        <div style={{ fontWeight: 700, fontSize: '20px', color: '#2563eb' }}>Arshin Verifier</div>
        <nav style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
          <Link to="/dashboard" style={{ textDecoration: 'none', color: '#374151', fontWeight: 500 }}>Dashboard</Link>
          <Link to="/jobs" style={{ textDecoration: 'none', color: '#374151', fontWeight: 500 }}>История проверок</Link>
          <button onClick={logout} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontWeight: 500, fontSize: '16px' }}>Выйти</button>
        </nav>
      </header>
      <main style={{ padding: '32px', maxWidth: '1200px', margin: '0 auto' }}>
        {children}
      </main>
    </div>
  );
};

// Защита роутов от неавторизованных пользователей
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
};

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Редирект с корня на дашборд */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        
        {/* Публичный роут */}
        <Route path="/login" element={<LoginPage />} />
        
        {/* Защищенные роуты */}
        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/jobs" element={<ProtectedRoute><JobsPage /></ProtectedRoute>} />
        <Route path="/jobs/:jobId" element={<ProtectedRoute><JobDetailsPage /></ProtectedRoute>} />
        
        {/* 404 для всех остальных путей */}
        <Route path="*" element={
          <div style={{ textAlign: 'center', marginTop: '100px' }}>
            <h1>404</h1>
            <p className="muted">Страница не найдена</p>
            <br />
            <Link to="/dashboard" style={{ color: '#2563eb' }}>Вернуться на главную</Link>
          </div>
        } />
      </Routes>
    </BrowserRouter>
  );
}
