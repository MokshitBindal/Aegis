// src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import DeviceDetailsPage from "./pages/DeviceDetailsPage";
import AlertsPage from "./pages/AlertsPage";
import { AuthProvider, useAuth } from "./contexts/AuthContext";

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { token: contextToken } = useAuth(); // Get token from context
  const storedToken = localStorage.getItem("aegis_token"); // Get token from storage

  // --- ADD LOG HERE ---
  console.log("ProtectedRoute Check:", { contextToken, storedToken });
  // --------------------

  const isAuthenticated = contextToken || storedToken;

  if (!isAuthenticated) {
    console.log("ProtectedRoute: Not authenticated, redirecting to /login"); // Optional log
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function AppRoutes() {
  // ... (No changes in AppRoutes function)
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
      <Route
        path="/device/:agentId"
        element={
          <ProtectedRoute>
            <DeviceDetailsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/alerts"
        element={
          <ProtectedRoute>
            <AlertsPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  // ... (No changes in App component)
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
