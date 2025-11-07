import React, { useEffect, useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
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
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [hostnameFilter, setHostnameFilter] = useState<string>("all");
  const [processFilter, setProcessFilter] = useState<string>("all");
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const logsContainerRef = useRef<HTMLDivElement>(null);

  // Fetch historical logs on mount
  useEffect(() => {
    const fetchLogs = async () => {
      try {
        setLoading(true);
        const params: any = { limit: 100 };
        if (deviceId) {
          params.agent_id = deviceId;
        }
        const response = await api.get(`/api/query/logs`, { params });
        setLogs(response.data.reverse()); // Reverse to show oldest first
      } catch (error) {
        console.error("Failed to fetch logs:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
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

  // Filter logs by severity, search, hostname, and process
  const filteredLogs = logs.filter((log) => {
    // Severity filter
    if (severityFilter !== "all") {
      const severityName = getSeverityName(log.severity).toLowerCase();
      if (severityName !== severityFilter.toLowerCase()) return false;
    }

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      if (
        !log.message.toLowerCase().includes(query) &&
        !log.hostname.toLowerCase().includes(query) &&
        !(log.process_name?.toLowerCase().includes(query) ?? false)
      ) {
        return false;
      }
    }

    // Hostname filter
    if (hostnameFilter !== "all" && log.hostname !== hostnameFilter) {
      return false;
    }

    // Process filter
    if (processFilter !== "all" && log.process_name !== processFilter) {
      return false;
    }

    return true;
  });

  // Get unique hostnames and processes for filters
  const uniqueHostnames = Array.from(new Set(logs.map((log) => log.hostname)));
  const uniqueProcesses = Array.from(
    new Set(logs.map((log) => log.process_name).filter(Boolean))
  );

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
        <Link
          to="/"
          className="text-sm text-blue-600 hover:text-blue-800 hover:underline mb-2 inline-block"
        >
          ← Back to Dashboard
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Live Logs</h1>
            <p className="text-sm text-gray-500 mt-1">
              {deviceId ? `Device: ${deviceId}` : "All Devices"}
            </p>
          </div>

          <div className="flex items-center gap-4">
            {/* Search Box */}
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">
                Search:
              </label>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search logs..."
                className="px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-900 bg-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 w-64"
              />
            </div>

            {/* Hostname Filter */}
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">Host:</label>
              <select
                value={hostnameFilter}
                onChange={(e) => setHostnameFilter(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All</option>
                {uniqueHostnames.map((hostname) => (
                  <option key={hostname} value={hostname}>
                    {hostname}
                  </option>
                ))}
              </select>
            </div>

            {/* Process Filter */}
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">
                Process:
              </label>
              <select
                value={processFilter}
                onChange={(e) => setProcessFilter(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All</option>
                {uniqueProcesses.map((process) => (
                  <option key={process} value={process}>
                    {process}
                  </option>
                ))}
              </select>
            </div>

            {/* Severity Filter */}
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">
                Severity:
              </label>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                onClick={() => setSelectedLog(log)}
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md hover:border-blue-300 transition-all cursor-pointer"
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

      {/* Log Details Modal */}
      {selectedLog && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
          onClick={() => setSelectedLog(null)}
        >
          <div
            className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">
                Log Details
              </h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(
                      JSON.stringify(selectedLog, null, 2)
                    );
                    alert("Log copied to clipboard!");
                  }}
                  className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                  Copy JSON
                </button>
                <button
                  onClick={() => setSelectedLog(null)}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <svg
                    className="w-6 h-6"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
            </div>

            <div className="p-6">
              {/* Severity Badge */}
              <div className="mb-4">
                <span
                  className={`px-3 py-1.5 text-sm font-semibold rounded-md border ${getSeverityColor(
                    selectedLog.severity
                  )}`}
                >
                  {getSeverityName(selectedLog.severity).toUpperCase()}
                </span>
              </div>

              {/* Log Fields */}
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Timestamp
                  </label>
                  <p className="text-sm text-gray-900 font-mono mt-1">
                    {formatTime(selectedLog.timestamp)}
                  </p>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Hostname
                  </label>
                  <p className="text-sm text-gray-900 mt-1">
                    {selectedLog.hostname}
                  </p>
                </div>

                {selectedLog.process_name && (
                  <div>
                    <label className="text-sm font-medium text-gray-500">
                      Process
                    </label>
                    <p className="text-sm text-gray-900 mt-1">
                      {selectedLog.process_name}
                    </p>
                  </div>
                )}

                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Facility
                  </label>
                  <p className="text-sm text-gray-900 font-mono mt-1">
                    {selectedLog.facility}
                  </p>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Agent ID
                  </label>
                  <p className="text-sm text-gray-900 font-mono mt-1">
                    {selectedLog.agent_id}
                  </p>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Message
                  </label>
                  <div className="mt-1 p-3 bg-gray-50 rounded-md border border-gray-200">
                    <p className="text-sm text-gray-900 whitespace-pre-wrap break-words">
                      {selectedLog.message}
                    </p>
                  </div>
                </div>

                {/* Raw JSON */}
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Raw JSON
                  </label>
                  <pre className="mt-1 p-3 bg-gray-900 text-gray-100 rounded-md text-xs overflow-x-auto">
                    {JSON.stringify(selectedLog, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LogsPage;
