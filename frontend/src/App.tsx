import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/auth';
import Login from './pages/Auth/Login';
import Register from './pages/Auth/Register';
import ProjectList from './pages/Project/ProjectList';
import ProjectDetail from './pages/Project/ProjectDetail';
import Layout from './components/layout/Layout';

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
    <Layout>
      <Routes>
        <Route path="/" element={<ProjectList />} />
        <Route path="/project/:id" element={<ProjectDetail />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Layout>
  );
}

export default App;