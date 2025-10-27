// src/pages/AlertsPage.tsx

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Link } from "react-router-dom";

interface Alert {
  id: number;
  rule_name: string;
  details: Record<string, any> | null;
  severity: string;
  created_at: string;
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // We'll also listen for WebSocket alerts later

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        setLoading(true);
        const response = await api.get("/api/alerts");
        setAlerts(response.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || "Failed to load alerts");
      } finally {
        setLoading(false);
      }
    };
    fetchAlerts();
  }, []);

  return (
    <div className="container p-8 mx-auto">
      <header className="pb-4 border-b border-gray-700">
        <Link to="/" className="text-sm text-blue-400 hover:underline">
          &larr; Back to Dashboard
        </Link>
        <h1 className="text-3xl font-bold">Security Alerts</h1>
      </header>
      <main className="mt-8">
        <div className="overflow-hidden bg-gray-800 rounded-lg shadow">
          {loading && <p className="p-4">Loading alerts...</p>}
          {error && <p className="p-4 text-red-400">{error}</p>}
          {!loading && !error && (
            <table className="min-w-full divide-y divide-gray-700">
              <thead className="bg-gray-700">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">
                    Timestamp
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
                    <td colSpan={4} className="p-4 text-center">
                      No alerts found.
                    </td>
                  </tr>
                ) : (
                  alerts.map((alert) => (
                    <tr key={alert.id} className="hover:bg-gray-700">
                      <td className="px-4 py-2 text-xs text-gray-400 whitespace-nowrap">
                        {new Date(alert.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-2 text-sm">{alert.rule_name}</td>
                      <td className="px-4 py-2 text-sm">{alert.severity}</td>
                      <td className="px-4 py-2 text-xs text-gray-400">
                        {alert.details ? JSON.stringify(alert.details) : "N/A"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  );
}
