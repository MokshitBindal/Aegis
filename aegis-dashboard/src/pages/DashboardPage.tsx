// src/pages/DashboardPage.tsx
import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../lib/api";
import { useWebSocket } from "../hooks/useWebSocket";
import { Link } from "react-router-dom";
import InviteTokenModal from "../components/InviteTokenModal";

interface Device {
  id: number;
  agent_id: string;
  name: string;
  hostname: string;
  registered_at: string;
}
type DeviceStatusMap = Record<string, "online" | "offline">;

export default function DashboardPage() {
  const { logout, userInfo, isOwner, isAdmin } = useAuth();
  const navigate = useNavigate();
  const [devices, setDevices] = useState<Device[]>([]);
  const [statuses, setStatuses] = useState<DeviceStatusMap>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Invite token modal state
  const [showTokenModal, setShowTokenModal] = useState(false);
  const [inviteToken, setInviteToken] = useState<string | null>(null);
  const [tokenExpiresAt, setTokenExpiresAt] = useState<string | null>(null);
  const [generatingToken, setGeneratingToken] = useState(false);

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

        // First, refresh all device statuses
        try {
          await api.post("/api/devices/refresh-status");
        } catch (err) {
          console.error("Failed to refresh device statuses:", err);
          // Continue even if status refresh fails
        }

        // Then fetch devices with updated statuses
        const response = await api.get("/api/devices");
        setDevices(response.data);
        const initialStatuses: DeviceStatusMap = {};
        for (const device of response.data) {
          // Use the status from the server
          initialStatuses[device.agent_id] = device.status || "offline";
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

  const handleLogout = (): void => {
    logout();
    navigate("/login");
  };

  const handleGenerateToken = async (): Promise<void> => {
    try {
      setGeneratingToken(true);
      const response = await api.post("/api/device/create-invitation");
      setInviteToken(response.data.token);
      setTokenExpiresAt(response.data.expires_at);
      setShowTokenModal(true);
    } catch (err: any) {
      console.error("Failed to generate token:", err);
      alert(
        err.response?.data?.detail ||
          "Failed to generate invitation token. Please try again."
      );
    } finally {
      setGeneratingToken(false);
    }
  };

  const handleCloseModal = (): void => {
    setShowTokenModal(false);
    setInviteToken(null);
    setTokenExpiresAt(null);
  };

  return (
    <div className="container p-8 mx-auto">
      <header className="flex items-center justify-between pb-4 border-b border-gray-700">
        <div>
          <h1 className="text-3xl font-bold">Aegis Dashboard</h1>
          {userInfo && (
            <p className="text-sm text-gray-400 mt-1">
              Logged in as{" "}
              <span className="font-medium text-gray-300">
                {userInfo.email}
              </span>{" "}
              (
              <span className="capitalize">
                {userInfo.role.replace("_", " ")}
              </span>
              )
            </p>
          )}
        </div>
        <button
          onClick={handleLogout}
          className="px-4 py-2 font-medium text-white bg-red-600 rounded-md hover:bg-red-700"
        >
          Logout
        </button>
      </header>

      {/* Role-based Navigation */}
      <nav className="mt-6 flex gap-4 flex-wrap">
        <Link
          to="/logs"
          className="px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600 transition-colors"
        >
          System Logs
        </Link>
        <Link
          to="/alerts"
          className="px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600 transition-colors"
        >
          View Alerts
        </Link>
        <Link
          to="/commands"
          className="px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600 transition-colors"
        >
          Command History
        </Link>
        {(isAdmin || isOwner) && (
          <Link
            to="/alert-triage"
            className="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 transition-colors"
          >
            🔍 Alert Triage
          </Link>
        )}
        {isOwner && (
          <Link
            to="/user-management"
            className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors"
          >
            👥 User Management
          </Link>
        )}
      </nav>

      <main className="mt-8">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-semibold">My Devices</h2>
          <div className="flex gap-4">
            <button
              onClick={handleGenerateToken}
              disabled={generatingToken}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:bg-gray-600 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {generatingToken ? (
                <>
                  <svg
                    className="animate-spin h-5 w-5 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  Generating...
                </>
              ) : (
                <>
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 4v16m8-8H4"
                    />
                  </svg>
                  Generate Invite Token
                </>
              )}
            </button>
          </div>
        </div>
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
                    <li
                      key={device.id}
                      className="p-4 hover:bg-gray-700 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <p className="text-lg font-semibold">{device.name}</p>
                          <p className="text-sm text-gray-400">
                            {device.hostname} ({device.agent_id.substring(0, 8)}
                            ...)
                          </p>
                        </div>

                        <div className="flex items-center gap-4">
                          {/* Quick Action Buttons */}
                          <div className="flex gap-2">
                            <Link
                              to={`/logs/${device.agent_id}`}
                              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                              onClick={(e) => e.stopPropagation()}
                            >
                              Logs
                            </Link>
                            <Link
                              to={`/commands/${device.agent_id}`}
                              className="px-3 py-1.5 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                              onClick={(e) => e.stopPropagation()}
                            >
                              Commands
                            </Link>
                            <Link
                              to={`/device/${device.agent_id}/metrics`}
                              className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors"
                              onClick={(e) => e.stopPropagation()}
                            >
                              Metrics
                            </Link>
                            <Link
                              to={`/alerts?deviceId=${device.agent_id}`}
                              className="px-3 py-1.5 text-sm bg-orange-600 text-white rounded-md hover:bg-orange-700 transition-colors"
                              onClick={(e) => e.stopPropagation()}
                            >
                              Alerts
                            </Link>
                            <Link
                              to={`/processes/${device.agent_id}`}
                              className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
                              onClick={(e) => e.stopPropagation()}
                            >
                              Processes
                            </Link>
                          </div>

                          {/* Status Badge */}
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
                              {new Date(
                                device.registered_at
                              ).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                      </div>
                    </li>
                  );
                })
              )}
            </ul>
          )}
        </div>
      </main>

      {/* Invite Token Modal */}
      <InviteTokenModal
        isOpen={showTokenModal}
        onClose={handleCloseModal}
        token={inviteToken}
        expiresAt={tokenExpiresAt}
      />
    </div>
  );
}
