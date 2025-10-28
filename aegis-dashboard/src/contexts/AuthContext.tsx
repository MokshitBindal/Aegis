// src/contexts/AuthContext.tsx
import {
  createContext,
  useContext,
  useState,
  type ReactNode,
  useEffect,
} from "react";
import { authApi } from "../lib/api";

interface AuthContextType {
  token: string | null;
  login: (email: string, pass: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(
    localStorage.getItem("aegis_token")
  );

  useEffect(() => {
    // Persist token changes to localStorage
    console.log('AuthContext useEffect: Token changed to:', token);
    if (token) {
      console.log('AuthContext useEffect: Setting token in localStorage');
      localStorage.setItem('aegis_token', token);
    } else {
      console.log('AuthContext useEffect: Removing token from localStorage');
      localStorage.removeItem('aegis_token');
    }
  }, [token]);

  const login = async (email: string, pass: string) => {
    // FastAPI's OAuth2 form expects URL-encoded data
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", pass);

    try {
      const response = await authApi.post("/auth/login", formData, {
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      });

      // --- ADD LOGS HERE ---
      console.log("AuthContext: API Login Response:", response.data);
      const { access_token } = response.data;
      console.log("AuthContext: Extracted Token:", access_token);
      // --------------------

      setToken(access_token);
    } catch (err) {
      console.error("Login failed:", err);
      throw new Error("Login Failed");
    }
  };

  const logout = () => {
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// This is a custom hook to easily access the context
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
