// src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import type { ReactNode } from "react"; // <--- FIX IS HERE

// This component protects routes that require a login
function ProtectedRoute({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  if (!token) {
    // If no token, redirect to the login page
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      {/* We'll add signup and other routes later */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

// We wrap our entire App in the AuthProvider
// so all components can access the login state
export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-900 text-white">
          <AppRoutes />
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}
