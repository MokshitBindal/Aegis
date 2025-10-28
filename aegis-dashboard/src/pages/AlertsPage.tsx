// src/pages/AlertsPage.tsx

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { Link } from "react-router-dom";

interface Alert {
  id: number;
  agent_id: string | null;
  rule_name: string;
  details: Record<string, any> | null;
  severity: string;
  created_at: string;
}

interface Device {
  id: number;
  agent_id: string;
  name: string;
  hostname: string;
}

export default function AlertsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const deviceIdFromUrl = searchParams.get("deviceId");

  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>(
    deviceIdFromUrl || "all"
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch devices for filter dropdown
  useEffect(() => {
    const fetchDevices = async () => {
      try {
        const response = await api.get("/api/devices");
        setDevices(response.data);
      } catch (err) {
        console.error("Failed to load devices:", err);
      }
    };
    fetchDevices();
  }, []);

  // Fetch alerts based on selected device
  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        setLoading(true);
        const params: any = {};
        if (selectedDevice && selectedDevice !== "all") {
          params.agent_id = selectedDevice;
        }
        const response = await api.get("/api/alerts", { params });
        setAlerts(response.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || "Failed to load alerts");
      } finally {
        setLoading(false);
      }
    };
    fetchAlerts();
  }, [selectedDevice]);

  // Handle device filter change
  const handleDeviceChange = (deviceId: string) => {
    setSelectedDevice(deviceId);
    if (deviceId === "all") {
      setSearchParams({});
    } else {
      setSearchParams({ deviceId });
    }
  };

  // Get severity color
  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "critical":
        return "bg-red-100 text-red-800 border-red-200";
      case "high":
        return "bg-orange-100 text-orange-800 border-orange-200";
      case "medium":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "low":
        return "bg-blue-100 text-blue-800 border-blue-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  return (
    <div className="container p-8 mx-auto">
      <header className="pb-4 border-b border-gray-700">
        <Link to="/" className="text-sm text-blue-400 hover:underline">
          &larr; Back to Dashboard
        </Link>
        <div className="flex items-center justify-between mt-4">
          <h1 className="text-3xl font-bold">Security Alerts</h1>

          {/* Device Filter */}
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-gray-300">
              Filter by Device:
            </label>
            <select
              value={selectedDevice}
              onChange={(e) => handleDeviceChange(e.target.value)}
              className="px-4 py-2 bg-gray-800 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Devices</option>
              {devices.map((device) => (
                <option key={device.id} value={device.agent_id}>
                  {device.name} ({device.hostname})
                </option>
              ))}
            </select>
            <div className="px-3 py-2 bg-blue-50 text-blue-700 rounded-md text-sm font-medium">
              {alerts.length} alert
              {alerts.length !== 1 ? "s" : ""}
            </div>
          </div>
        </div>
      </header>
      <main className="mt-8">
        <div className="overflow-hidden bg-gray-800 rounded-lg shadow">
          {loading && (
            <div className="flex items-center justify-center p-8">
              <svg
                className="animate-spin h-8 w-8 text-blue-600"
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
              <span className="ml-3">Loading alerts...</span>
            </div>
          )}
          {error && <p className="p-4 text-red-400">{error}</p>}
          {!loading && !error && (
            <table className="min-w-full divide-y divide-gray-700">
              <thead className="bg-gray-700">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">
                    Timestamp
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">
                    Device
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">
                    Rule
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">
                    Severity
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">
                    Details
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {alerts.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="p-8 text-center">
                      <div className="text-gray-400">
                        <svg
                          className="mx-auto h-12 w-12 text-gray-500"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                          />
                        </svg>
                        <p className="mt-2 text-lg font-medium">
                          No alerts found
                        </p>
                        <p className="mt-1 text-sm">
                          {selectedDevice !== "all"
                            ? "No alerts for this device"
                            : "Your devices are secure"}
                        </p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  alerts.map((alert) => {
                    const device = devices.find(
                      (d) => d.agent_id === alert.agent_id
                    );
                    return (
                      <tr key={alert.id} className="hover:bg-gray-700">
                        <td className="px-4 py-2 text-xs text-gray-400 whitespace-nowrap">
                          {new Date(alert.created_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-2 text-sm">
                          {device ? (
                            <Link
                              to={`/device/${device.agent_id}`}
                              className="text-blue-400 hover:underline"
                            >
                              {device.name}
                            </Link>
                          ) : (
                            <span className="text-gray-500">Unknown</span>
                          )}
                        </td>
                        <td className="px-4 py-2 text-sm">{alert.rule_name}</td>
                        <td className="px-4 py-2">
                          <span
                            className={`px-2 py-1 text-xs font-semibold rounded-md border ${getSeverityColor(
                              alert.severity
                            )}`}
                          >
                            {alert.severity.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-xs text-gray-400">
                          {alert.details ? (
                            <pre className="max-w-md overflow-auto">
                              {JSON.stringify(alert.details, null, 2)}
                            </pre>
                          ) : (
                            "N/A"
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  );
}
