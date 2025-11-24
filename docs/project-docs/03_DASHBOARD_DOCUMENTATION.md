# Aegis Dashboard Documentation

**Component:** Aegis Dashboard (Web Frontend)  
**Framework:** React 18 + TypeScript + Vite  
**UI Library:** shadcn/ui + Tailwind CSS  
**Author:** Mokshit Bindal  
**Last Updated:** November 19, 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Key Features](#key-features)
4. [User Interface](#user-interface)
5. [State Management](#state-management)
6. [API Integration](#api-integration)
7. [Authentication Flow](#authentication-flow)
8. [Deployment](#deployment)
9. [Development Guide](#development-guide)

---

## Overview

### Purpose

The Aegis Dashboard is the web-based user interface for security analysts, administrators, and owners to monitor systems, triage alerts, investigate incidents, and manage the SIEM platform.

### Key Technologies

- **React 18:** Modern UI library with hooks
- **TypeScript:** Type-safe JavaScript
- **Vite:** Fast build tool and dev server
- **Tailwind CSS:** Utility-first CSS framework
- **shadcn/ui:** High-quality React components
- **React Router:** Client-side routing
- **Axios:** HTTP client for API calls
- **Recharts:** Data visualization library

### System Requirements

- **Node.js:** 18.0+ or 20.0+
- **npm:** 9.0+ or pnpm/yarn
- **Browser:** Modern browser (Chrome, Firefox, Edge, Safari)

---

## Architecture

### Component Structure

```
aegis-dashboard/src/
├── main.tsx                 # App entry point
├── App.tsx                  # Root component with routing
├── pages/                   # Page components
│   ├── Login.tsx           # Login page
│   ├── Dashboard.tsx       # Main dashboard
│   ├── Alerts.tsx          # Alert management
│   ├── Devices.tsx         # Device monitoring
│   ├── Incidents.tsx       # Incident triage
│   ├── Analytics.tsx       # Charts and analytics
│   ├── MLData.tsx          # ML training data export
│   └── Settings.tsx        # User settings
├── components/             # Reusable UI components
│   ├── ui/                # shadcn/ui base components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── table.tsx
│   │   └── ...
│   ├── AlertCard.tsx      # Alert display component
│   ├── DeviceStatus.tsx   # Device status indicator
│   ├── Chart.tsx          # Chart wrapper
│   └── Navbar.tsx         # Navigation bar
├── contexts/              # React Context providers
│   └── AuthContext.tsx    # Authentication state
├── hooks/                 # Custom React hooks
│   ├── useAuth.tsx       # Authentication hook
│   ├── useAlerts.tsx     # Alerts data hook
│   └── useDevices.tsx    # Devices data hook
├── lib/                   # Utilities
│   ├── api.ts            # API client configuration
│   └── utils.ts          # Helper functions
└── assets/               # Static assets
    └── logo.svg
```

### Data Flow

```
User Interaction
    ↓
React Component
    ↓
Custom Hook (useAlerts, useDevices, etc.)
    ↓
API Client (Axios)
    ↓
Aegis Server API
    ↓
PostgreSQL Database
    ↓
Response flows back up the chain
    ↓
Component Re-renders with New Data
```

---

## Key Features

### 1. Real-Time Dashboard

**Overview Metrics:**

- Total devices online/offline
- Active alerts by severity
- Recent incidents
- System health status

**Live Updates:**

- WebSocket connection for real-time alerts
- Auto-refresh every 30 seconds
- Visual indicators for new activity

### 2. Alert Management

**Features:**

- View all alerts with filtering (severity, status, device)
- Sort by timestamp, severity, or status
- Assign alerts to analysts
- Add notes and resolve alerts
- Bulk operations (assign multiple, resolve multiple)

**Alert Card Display:**

```tsx
<AlertCard alert={alert} onAssign={handleAssign} onResolve={handleResolve} />
```

### 3. Device Monitoring

**Features:**

- List all registered devices
- View device details (OS, version, last seen)
- Real-time status indicators (online/offline)
- Device health metrics
- Historical data timeline

### 4. Incident Triage

**Features:**

- View correlated incidents
- See related alerts grouped together
- Assign incident to analyst
- Add investigation notes
- Mark as resolved with summary

### 5. ML Data Export

**Features:**

- View unexported data counts
- Monitor export thresholds
- Manually trigger exports
- Download exported CSV files
- Configure export settings

### 6. Analytics & Visualization

**Charts:**

- Alerts over time (line chart)
- Severity distribution (pie chart)
- Top devices by alert count (bar chart)
- CPU/Memory trends (area chart)

**Library:** Recharts

---

## User Interface

### Login Page

```tsx
// src/pages/Login.tsx
export function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (error) {
      toast.error("Login failed");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Login to Aegis SIEM</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit}>
          <Input type="email" value={email} onChange={setEmail} />
          <Input type="password" value={password} onChange={setPassword} />
          <Button type="submit">Login</Button>
        </form>
      </CardContent>
    </Card>
  );
}
```

### Dashboard Layout

```tsx
// src/App.tsx
function App() {
  return (
    <AuthProvider>
      <Router>
        <Navbar />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/devices" element={<Devices />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/ml-data" element={<MLData />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}
```

### Responsive Design

**Breakpoints (Tailwind):**

- `sm`: 640px (Mobile)
- `md`: 768px (Tablet)
- `lg`: 1024px (Desktop)
- `xl`: 1280px (Large Desktop)

**Example:**

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  <MetricCard /> {/* 1 column on mobile, 2 on tablet, 4 on desktop */}
</div>
```

---

## State Management

### Authentication Context

```tsx
// src/contexts/AuthContext.tsx
interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(
    localStorage.getItem("aegis_token")
  );

  const login = async (email: string, password: string) => {
    const response = await api.post("/auth/login", {
      username: email,
      password,
    });
    const { access_token } = response.data;

    setToken(access_token);
    localStorage.setItem("aegis_token", access_token);

    // Decode JWT to get user info
    const decoded = jwtDecode(access_token);
    setUser({ email: decoded.sub, role: decoded.role });
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("aegis_token");
  };

  return (
    <AuthContext.Provider
      value={{ user, token, login, logout, isAuthenticated: !!token }}
    >
      {children}
    </AuthContext.Provider>
  );
}
```

### Custom Hooks

**useAlerts Hook:**

```tsx
// src/hooks/useAlerts.tsx
export function useAlerts(filters?: AlertFilters) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const { token } = useAuth();

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get("/api/alerts", {
        headers: { Authorization: `Bearer ${token}` },
        params: filters,
      });
      setAlerts(response.data.alerts);
    } catch (error) {
      toast.error("Failed to fetch alerts");
    } finally {
      setLoading(false);
    }
  }, [token, filters]);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  const assignAlert = async (alertId: number, userId: number) => {
    await api.post(
      `/api/alerts/${alertId}/assign`,
      { assigned_to: userId },
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    fetchAlerts();
  };

  const resolveAlert = async (alertId: number, notes: string) => {
    await api.post(
      `/api/alerts/${alertId}/resolve`,
      { resolution_notes: notes },
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    fetchAlerts();
  };

  return { alerts, loading, fetchAlerts, assignAlert, resolveAlert };
}
```

---

## API Integration

### API Client Configuration

```tsx
// src/lib/api.ts
import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("aegis_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login on auth failure
      localStorage.removeItem("aegis_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;
```

### API Calls

**Fetch Alerts:**

```tsx
const response = await api.get("/api/alerts", {
  params: {
    severity: "high",
    assignment_status: "unassigned",
    limit: 50,
  },
});
```

**Assign Alert:**

```tsx
await api.post(`/api/alerts/${alertId}/assign`, {
  assigned_to: userId,
});
```

**Fetch Devices:**

```tsx
const response = await api.get("/api/devices");
```

---

## Authentication Flow

### Login Sequence

```
1. User enters email/password
      ↓
2. POST /auth/login
      ↓
3. Server validates credentials
      ↓
4. Server returns JWT token
      ↓
5. Dashboard stores token in localStorage
      ↓
6. Dashboard decodes JWT to get user info
      ↓
7. AuthContext updates user state
      ↓
8. App redirects to /dashboard
      ↓
9. All subsequent API calls include token in Authorization header
```

### Protected Routes

```tsx
// src/components/ProtectedRoute.tsx
export function ProtectedRoute({ children, requiredRole }) {
  const { isAuthenticated, user } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  if (requiredRole && user.role !== requiredRole) {
    return <div>Access Denied</div>;
  }

  return children;
}

// Usage:
<Route
  path="/admin/users"
  element={
    <ProtectedRoute requiredRole="owner">
      <UserManagement />
    </ProtectedRoute>
  }
/>;
```

### Token Refresh

Currently tokens have 7-day expiration. For auto-refresh:

```tsx
useEffect(() => {
  if (token) {
    const decoded = jwtDecode(token);
    const expiresIn = decoded.exp * 1000 - Date.now();

    if (expiresIn < 86400000) {
      // Less than 1 day
      // Implement token refresh logic
      refreshToken();
    }
  }
}, [token]);
```

---

## Deployment

### Development

```bash
cd aegis-dashboard
npm install
npm run dev  # Starts dev server on port 5173
```

**Environment Variables (`.env`):**

```
VITE_API_URL=http://localhost:8000
```

### Production Build

```bash
npm run build
# Output: dist/ folder with static files
```

### Deployment Options

**1. Static Hosting (Nginx):**

```nginx
server {
    listen 80;
    server_name dashboard.aegis.com;
    root /var/www/aegis-dashboard/dist;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

**2. Docker:**

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**3. Vercel/Netlify:**

```bash
# Install CLI
npm i -g vercel

# Deploy
cd aegis-dashboard
vercel --prod
```

---

## Development Guide

### Adding a New Page

1. Create page component in `src/pages/`:

```tsx
// src/pages/NewPage.tsx
export function NewPage() {
  return (
    <div>
      <h1>New Page</h1>
    </div>
  );
}
```

2. Add route in `App.tsx`:

```tsx
<Route path="/new-page" element={<NewPage />} />
```

3. Add navigation link in `Navbar.tsx`:

```tsx
<Link to="/new-page">New Page</Link>
```

### Creating a Custom Hook

```tsx
// src/hooks/useCustomHook.tsx
export function useCustomHook() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch data logic
  }, []);

  return { data, loading };
}
```

### Adding a shadcn/ui Component

```bash
npx shadcn-ui@latest add dialog
# Adds src/components/ui/dialog.tsx
```

### Styling Guidelines

**Tailwind CSS Conventions:**

```tsx
// Good: Utility classes
<div className="flex items-center gap-4 p-4 bg-white rounded-lg shadow">
  <Button className="bg-blue-500 hover:bg-blue-600">Click</Button>
</div>

// Use conditional classes
<div className={cn(
  "base-classes",
  isActive && "active-classes",
  isError && "error-classes"
)}>
```

### Type Definitions

```tsx
// src/types.ts
export interface Alert {
  id: number;
  rule_name: string;
  severity: "low" | "medium" | "high" | "critical";
  agent_id: string;
  details: Record<string, any>;
  assignment_status: "unassigned" | "assigned" | "resolved";
  assigned_to?: number;
  created_at: string;
  resolved_at?: string;
}

export interface Device {
  agent_id: string;
  hostname: string;
  os: string;
  status: "online" | "offline";
  last_seen: string;
}
```

---

## Testing

### Unit Tests (Vitest)

```tsx
// src/components/__tests__/AlertCard.test.tsx
import { render, screen } from "@testing-library/react";
import { AlertCard } from "../AlertCard";

describe("AlertCard", () => {
  it("renders alert data", () => {
    const alert = {
      id: 1,
      rule_name: "Test Alert",
      severity: "high",
      // ...
    };

    render(<AlertCard alert={alert} />);
    expect(screen.getByText("Test Alert")).toBeInTheDocument();
  });
});
```

### E2E Tests (Playwright)

```tsx
// tests/login.spec.ts
import { test, expect } from "@playwright/test";

test("user can login", async ({ page }) => {
  await page.goto("http://localhost:5173/login");
  await page.fill('[name="email"]', "owner@aegis.com");
  await page.fill('[name="password"]', "password");
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL("/dashboard");
});
```

---

## Performance Optimization

### Code Splitting

```tsx
// Lazy load pages
const Analytics = lazy(() => import("./pages/Analytics"));

<Route
  path="/analytics"
  element={
    <Suspense fallback={<Loading />}>
      <Analytics />
    </Suspense>
  }
/>;
```

### Memoization

```tsx
const AlertList = memo(({ alerts }) => {
  return alerts.map((alert) => <AlertCard key={alert.id} alert={alert} />);
});
```

### Virtualization (Large Lists)

```tsx
import { FixedSizeList } from "react-window";

<FixedSizeList height={600} itemCount={alerts.length} itemSize={100}>
  {({ index, style }) => (
    <div style={style}>
      <AlertCard alert={alerts[index]} />
    </div>
  )}
</FixedSizeList>;
```

---

**For More Information:**

- Agent Documentation: `01_AGENT_DOCUMENTATION.md`
- Server Documentation: `02_SERVER_DOCUMENTATION.md`
- ML Model Documentation: `04_ML_MODEL_DOCUMENTATION.md`
- Complete Project Overview: `05_PROJECT_OVERVIEW.md`
