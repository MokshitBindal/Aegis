import React, { useEffect, useState, useRef } from "react";
import { useParams } from "react-router-dom";
import { useWebSocket } from "../hooks/useWebSocket";
import { api } from "../lib/api";

interface LogEntry {
  id: number;
  agent_id: string;
  timestamp: string;
  message: string;
  severity: string;
  facility: string;
  hostname: string;
  process_name?: string;
}

const LogsPage: React.FC = () => {
  const { deviceId } = useParams<{ deviceId: string }>();
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [autoScroll, setAutoScroll] = useState(true);
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const logsEndRef = useRef<HTMLDivElement>(null);
  const logsContainerRef = useRef<HTMLDivElement>(null);

  // Fetch historical logs on mount
  useEffect(() => {
    const fetchLogs = async () => {
      try {
        setLoading(true);
        const response = await api.get(`/api/query/logs`, {
          params: {
            agent_id: deviceId,
            limit: 100,
          },
        });
        setLogs(response.data.reverse()); // Reverse to show oldest first
      } catch (error) {
        console.error("Failed to fetch logs:", error);
      } finally {
        setLoading(false);
      }
    };

    if (deviceId) {
      fetchLogs();
    }
  }, [deviceId]);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, autoScroll]);

  // Listen for real-time log updates via WebSocket
  useWebSocket((data) => {
    if (data.type === "new_log") {
      const logEntry: LogEntry = data.payload;

      // Only add logs for the current device (or all if no device selected)
      if (!deviceId || logEntry.agent_id === deviceId) {
        setLogs((prev) => {
          // Limit to last 500 logs to prevent memory issues
          const newLogs = [...prev, logEntry];
          return newLogs.slice(-500);
        });
      }
    }
  });

  // Handle manual scroll - disable auto-scroll if user scrolls up
  const handleScroll = () => {
    if (!logsContainerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = logsContainerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;

    setAutoScroll(isAtBottom);
  };

  // Filter logs by severity
  const filteredLogs = logs.filter((log) => {
    if (severityFilter === "all") return true;
    const severityName = getSeverityName(log.severity).toLowerCase();
    return severityName === severityFilter.toLowerCase();
  });

  // Get severity badge color
  const getSeverityColor = (severity: string) => {
    const level = getSeverityName(severity).toLowerCase();
    switch (level) {
      case "emergency":
      case "alert":
      case "critical":
      case "error":
        return "bg-red-100 text-red-800 border-red-200";
      case "warning":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "notice":
      case "info":
        return "bg-blue-100 text-blue-800 border-blue-200";
      case "debug":
        return "bg-gray-100 text-gray-800 border-gray-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  // Convert numeric severity to name
  const getSeverityName = (severity: string): string => {
    const severityMap: { [key: string]: string } = {
      "0": "Emergency",
      "1": "Alert",
      "2": "Critical",
      "3": "Error",
      "4": "Warning",
      "5": "Notice",
      "6": "Info",
      "7": "Debug",
    };
    return severityMap[severity] || severity;
  };

  // Format timestamp
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Live Logs</h1>
            <p className="text-sm text-gray-500 mt-1">
              {deviceId ? `Device: ${deviceId}` : "All Devices"}
            </p>
          </div>

          <div className="flex items-center gap-4">
            {/* Severity Filter */}
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">
                Severity:
              </label>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All</option>
                <option value="emergency">Emergency</option>
                <option value="alert">Alert</option>
                <option value="critical">Critical</option>
                <option value="error">Error</option>
                <option value="warning">Warning</option>
                <option value="notice">Notice</option>
                <option value="info">Info</option>
                <option value="debug">Debug</option>
              </select>
            </div>

            {/* Auto-scroll Toggle */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className="text-sm font-medium text-gray-700">
                Auto-scroll
              </span>
            </label>

            {/* Log Count */}
            <div className="px-3 py-2 bg-blue-50 text-blue-700 rounded-md text-sm font-medium">
              {filteredLogs.length} logs
            </div>
          </div>
        </div>
      </div>

      {/* Logs Container */}
      <div
        ref={logsContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4"
      >
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <svg
                className="animate-spin h-12 w-12 text-blue-600 mx-auto"
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
              <p className="mt-4 text-gray-600">Loading logs...</p>
            </div>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-400">
              <svg
                className="mx-auto h-16 w-16 text-gray-300"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <p className="mt-4 text-lg font-medium">No logs available</p>
              <p className="mt-2 text-sm">
                {deviceId
                  ? "Waiting for logs from this device..."
                  : "Start an agent to see logs appear here"}
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredLogs.map((log) => (
              <div
                key={log.id}
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start gap-3">
                  {/* Severity Badge */}
                  <span
                    className={`px-2 py-1 text-xs font-semibold rounded-md border ${getSeverityColor(
                      log.severity
                    )}`}
                  >
                    {getSeverityName(log.severity).toUpperCase()}
                  </span>

                  {/* Log Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs text-gray-500 font-mono">
                        {formatTime(log.timestamp)}
                      </span>
                      <span className="text-xs text-gray-400">•</span>
                      <span className="text-xs text-gray-600 font-medium">
                        {log.hostname}
                      </span>
                      {log.process_name && (
                        <>
                          <span className="text-xs text-gray-400">•</span>
                          <span className="text-xs text-gray-600">
                            {log.process_name}
                          </span>
                        </>
                      )}
                      <span className="text-xs text-gray-400">•</span>
                      <span className="text-xs text-gray-500 font-mono">
                        {log.facility}
                      </span>
                    </div>
                    <p className="text-sm text-gray-900 break-words">
                      {log.message}
                    </p>
                  </div>
                </div>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>
    </div>
  );
};

export default LogsPage;
