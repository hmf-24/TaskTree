import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/auth';
import Login from './pages/Auth/Login';
import Register from './pages/Auth/Register';
import Launcher from './pages/Workspace/Launcher';
import ProjectList from './pages/Project/ProjectList';
import ProjectDetail from './pages/Project/ProjectDetail';
import Settings from './pages/Settings/Settings';
import Layout from './components/layout/Layout';
import ReadHubHome from './pages/apps/ReadHub/ReadHubHome';
import ReadHubSettings from './pages/apps/ReadHub/ReadHubSettings';

function App() {
  const { isAuthenticated } = useAuthStore();

  return (
    <Routes>
      <Route path="/auth/*" element={!isAuthenticated ? <AuthRoutes /> : <Navigate to="/" />} />
      <Route path="/*" element={isAuthenticated ? <AppRoutes /> : <Navigate to="/auth/login" />} />
    </Routes>
  );
}

function AuthRoutes() {
  return (
    <Routes>
      <Route path="login" element={<Login />} />
      <Route path="register" element={<Register />} />
      <Route path="*" element={<Navigate to="/auth/login" />} />
    </Routes>
  );
}

function AppRoutes() {
  return (
    <Routes>
      {/* 工作台首页 — 无侧边栏的独立布局 */}
      <Route index element={<Launcher />} />

      {/* TaskTree 应用 — 带侧边栏的 Layout */}
      <Route path="app/tasktree" element={<Layout />}>
        <Route index element={<ProjectList />} />
        <Route path="project/:id" element={<ProjectDetail />} />
      </Route>

      {/* ReadHub 应用 — 带侧边栏的 Layout */}
      <Route path="app/readhub" element={<Layout />}>
        <Route index element={<ReadHubHome />} />
        <Route path="settings" element={<ReadHubSettings />} />
      </Route>

      {/* 设置 — 带侧边栏的 Layout */}
      <Route path="settings" element={<Layout />}>
        <Route index element={<Settings />} />
      </Route>

      {/* 兜底重定向 */}
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}

export default App;
