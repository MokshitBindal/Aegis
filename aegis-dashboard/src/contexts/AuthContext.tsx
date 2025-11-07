// src/contexts/AuthContext.tsx
import {
  createContext,
  useContext,
  useState,
  type ReactNode,
  useEffect,
} from "react";
import { authApi } from "../lib/api";

export type UserRole = "owner" | "admin" | "device_user";

export interface UserInfo {
  email: string;
  role: UserRole;
  userId: number;
}

interface AuthContextType {
  token: string | null;
  userInfo: UserInfo | null;
  login: (email: string, pass: string) => Promise<void>;
  logout: () => void;
  isOwner: boolean;
  isAdmin: boolean;
  isDeviceUser: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Helper function to decode JWT and extract user info
function decodeToken(token: string): UserInfo | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;

    const payload = JSON.parse(atob(parts[1]));

    return {
      email: payload.sub,
      role: payload.role,
      userId: payload.user_id,
    };
  } catch (err) {
    console.error("Failed to decode token:", err);
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(
    localStorage.getItem("aegis_token")
  );
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);

  // Decode token when it changes
  useEffect(() => {
    if (token) {
      const decoded = decodeToken(token);
      setUserInfo(decoded);
      console.log("AuthContext: Decoded user info:", decoded);
    } else {
      setUserInfo(null);
    }
  }, [token]);

  useEffect(() => {
    // Persist token changes to localStorage
    console.log("AuthContext useEffect: Token changed to:", token);
    if (token) {
      console.log("AuthContext useEffect: Setting token in localStorage");
      localStorage.setItem("aegis_token", token);
    } else {
      console.log("AuthContext useEffect: Removing token from localStorage");
      localStorage.removeItem("aegis_token");
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

  // Computed properties for role checks
  const isOwner = userInfo?.role === "owner";
  const isAdmin = userInfo?.role === "admin";
  const isDeviceUser = userInfo?.role === "device_user";

  return (
    <AuthContext.Provider
      value={{ token, userInfo, login, logout, isOwner, isAdmin, isDeviceUser }}
    >
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
