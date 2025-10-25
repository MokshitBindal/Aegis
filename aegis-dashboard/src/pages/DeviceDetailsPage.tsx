// src/pages/DeviceDetailsPage.tsx

import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";

// This is the shape of the log data from our new endpoint
interface Log {
  timestamp: string;
  hostname: string;
  message: string;
  // This is a JSON *string* from the server
  raw_data: string;
}

type Timeframe = "1h" | "6h" | "24h" | "7d";

export default function DeviceDetailsPage() {
  const { agentId } = useParams<{ agentId: string }>();
  const [logs, setLogs] = useState<Log[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeframe, setTimeframe] = useState<Timeframe>("24h");
  const [selectedLog, setSelectedLog] = useState<Log | null>(null);

  useEffect(() => {
    if (!agentId) return;

    const fetchLogs = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await api.get("/api/logs", {
          params: {
            agent_id: agentId,
            timeframe: timeframe,
            limit: 1000,
          },
        });
        setLogs(response.data);
      } catch (err: any) {
        console.error("Failed to fetch logs:", err);
        setError(err.response?.data?.detail || "Failed to load logs.");
      } finally {
        setLoading(false);
      }
    };
    fetchLogs();
  }, [agentId, timeframe]);

  // Helper function to pretty-print the JSON
  const getPrettyJson = (log: Log | null) => {
    if (!log) return null;
    try {
      // 1. Parse the raw_data string into an object
      const jsonObject = JSON.parse(log.raw_data);
      // 2. Stringify that object with formatting
      return JSON.stringify(jsonObject, null, 2);
    } catch (e) {
      console.error("Failed to parse raw_data:", e);
      // Fallback if JSON is malformed
      return "Invalid JSON data";
    }
  };

  return (
    <div className="container p-8 mx-auto flex flex-col h-screen">
      <header className="pb-4 border-b border-gray-700">
        <Link to="/" className="text-sm text-blue-400 hover:underline">
          &larr; Back to Dashboard
        </Link>
        <h1 className="text-3xl font-bold">Log Viewer</h1>
        <p className="text-sm text-gray-400">Agent ID: {agentId}</p>
      </header>

      {/* Timeframe Selector */}
      <div className="my-4">
        {/* ... (no changes here) ... */}
        {["1h", "6h", "24h", "7d"].map((tf) => (
          <button
            key={tf}
            onClick={() => setTimeframe(tf as Timeframe)}
            className={`px-3 py-1 mr-2 rounded-full ${
              timeframe === tf
                ? "bg-blue-600 text-white"
                : "bg-gray-700 text-gray-300"
            }`}
          >
            {tf}
          </button>
        ))}
      </div>

      {/* Log Content Area - This will fill the remaining height */}
      <div className="flex space-x-4 flex-1 min-h-0">
        {/* --- FIX 1: Log Table Container --- */}
        {/* We add max-h-full (to respect parent) and overflow-y-auto */}
        <div className="w-1/2 bg-gray-800 rounded-lg shadow overflow-y-auto max-h-full">
          <table className="min-w-full divide-y divide-gray-700">
            <thead className="bg-gray-700 sticky top-0">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">
                  Timestamp
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-300 uppercase">
                  Message
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {loading && (
                <tr>
                  <td colSpan={2} className="p-4 text-center">
                    Loading...
                  </td>
                </tr>
              )}
              {error && (
                <tr>
                  <td colSpan={2} className="p-4 text-center text-red-400">
                    {error}
                  </td>
                </tr>
              )}
              {!loading &&
                !error &&
                logs.map((log, index) => (
                  <tr
                    key={index}
                    onClick={() => setSelectedLog(log)}
                    className={`hover:bg-gray-700 cursor-pointer ${
                      selectedLog === log ? "bg-gray-700" : ""
                    }`}
                  >
                    <td className="px-4 py-2 text-xs text-gray-400 whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-2 text-sm truncate max-w-xs">
                      {log.message}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>

        {/* --- FIX 2: JSON Detail Viewer --- */}
        {/* We also add max-h-full to make its height consistent */}
        <div className="w-1/2 p-4 bg-gray-800 rounded-lg shadow flex flex-col max-h-full">
          <h3 className="text-lg font-semibold">Log Details</h3>
          {selectedLog ? (
            <pre className="mt-2 p-2 text-xs text-green-300 bg-gray-900 rounded overflow-auto flex-1">
              {/* Call our new helper function */}
              {getPrettyJson(selectedLog)}
            </pre>
          ) : (
            <p className="mt-2 text-gray-400">Select a log to see details</p>
          )}
        </div>
      </div>
    </div>
  );
}
