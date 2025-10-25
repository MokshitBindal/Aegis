// src/pages/DashboardPage.tsx
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../lib/api";
import { useWebSocket } from "../hooks/useWebSocket";
import { Link } from "react-router-dom"; // <--- 1. IMPORT LINK

// ... (interface Device and DeviceStatusMap are unchanged) ...
interface Device {
  id: number;
  agent_id: string;
  name: string;
  hostname: string;
  registered_at: string;
}
type DeviceStatusMap = Record<string, "online" | "offline">;

export default function DashboardPage() {
  const { logout } = useAuth();
  const [devices, setDevices] = useState<Device[]>([]);
  const [statuses, setStatuses] = useState<DeviceStatusMap>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleWsMessage = useCallback((data: any) => {
    if (data.type === "agent_status") {
      const { agent_id, status } = data.payload;
      setStatuses((prev) => ({ ...prev, [agent_id]: status }));
      setTimeout(() => {
        setStatuses((prev) => ({ ...prev, [agent_id]: "offline" }));
      }, 65000);
    }
  }, []);

  useWebSocket(handleWsMessage);

  useEffect(() => {
    const fetchDevices = async () => {
      try {
        setLoading(true);
        const response = await api.get("/api/devices");
        setDevices(response.data);
        const initialStatuses: DeviceStatusMap = {};
        for (const device of response.data) {
          initialStatuses[device.agent_id] = "offline";
        }
        setStatuses(initialStatuses);
      } catch (err) {
        console.error("Failed to fetch devices:", err);
        setError("Failed to load devices.");
      } finally {
        setLoading(false);
      }
    };
    fetchDevices();
  }, []);

  return (
    <div className="container p-8 mx-auto">
      <header className="flex items-center justify-between pb-4 border-b border-gray-700">
        <h1 className="text-3xl font-bold">Aegis Dashboard</h1>
        <button
          onClick={logout}
          className="px-4 py-2 font-medium text-white bg-red-600 rounded-md hover:bg-red-700"
        >
          Logout
        </button>
      </header>

      <main className="mt-8">
        <h2 className="text-2xl font-semibold">My Devices</h2>
        <div className="mt-4 overflow-hidden bg-gray-800 rounded-lg shadow">
          {loading && <p className="p-4">Loading devices...</p>}
          {error && <p className="p-4 text-red-400">{error}</p>}

          {!loading && !error && (
            <ul className="divide-y divide-gray-700">
              {devices.length === 0 ? (
                <li className="p-4">No devices registered yet.</li>
              ) : (
                devices.map((device) => {
                  const status = statuses[device.agent_id] || "offline";

                  return (
                    // --- 2. WRAP LIST ITEM IN A LINK ---
                    <Link
                      key={device.id}
                      to={`/device/${device.agent_id}`}
                      className="flex items-center justify-between p-4 hover:bg-gray-700"
                    >
                      <div>
                        <p className="text-lg font-semibold">{device.name}</p>
                        <p className="text-sm text-gray-400">
                          {device.hostname} ({device.agent_id.substring(0, 8)}
                          ...)
                        </p>
                      </div>
                      <div className="text-right">
                        <span
                          className={`inline-block px-3 py-1 text-sm rounded-full ${
                            status === "online"
                              ? "bg-green-800 text-green-300"
                              : "bg-gray-700 text-gray-400"
                          }`}
                        >
                          {status}
                        </span>
                        <p className="mt-1 text-xs text-gray-500">
                          Registered:{" "}
                          {new Date(device.registered_at).toLocaleDateString()}
                        </p>
                      </div>
                    </Link>
                  );
                })
              )}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}
