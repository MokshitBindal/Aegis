import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";

interface Process {
  id: number;
  agent_id: string;
  pid: number;
  name: string;
  exe: string | null;
  cmdline: string | null;
  username: string;
  status: string;
  create_time: string | null;
  ppid: number | null;
  cpu_percent: number | null;
  memory_percent: number | null;
  memory_rss: number | null;
  memory_vms: number | null;
  num_threads: number | null;
  num_fds: number | null;
  num_connections: number | null;
  connection_details: any;
  collected_at: string;
}

interface ProcessSummary {
  agent_id: string;
  collected_at: string;
  total_processes: number;
  total_threads: number;
  total_connections: number;
  cpu_count: number;
  system_cpu_percent?: number;
  avg_cpu_percent: number;
  total_cpu_percent: number;
  cpu_utilization_percent: number;
  avg_memory_percent: number;
  total_memory_percent: number;
  total_memory_rss_mb: number;
  processes_by_user: Array<{ username: string; count: number }>;
}

const ProcessesPage: React.FC = () => {
  const { deviceId } = useParams<{ deviceId: string }>();

  // Cache keys for localStorage (persistent across sessions)
  const cacheKey = `processes_${deviceId}`;
  const summaryCacheKey = `processes_summary_${deviceId}`;

  // Initialize state from localStorage if available
  const [processes, setProcesses] = useState<Process[]>(() => {
    try {
      const cached = localStorage.getItem(cacheKey);
      return cached ? JSON.parse(cached) : [];
    } catch {
      return [];
    }
  });
  const [summary, setSummary] = useState<ProcessSummary | null>(() => {
    try {
      const cached = localStorage.getItem(summaryCacheKey);
      return cached ? JSON.parse(cached) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterUser, setFilterUser] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [sortBy, setSortBy] = useState<"cpu" | "memory" | "pid" | "name">(
    "cpu"
  );
  const [selectedProcess, setSelectedProcess] = useState<Process | null>(null);

  useEffect(() => {
    if (!deviceId) return;

    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch latest processes and summary in parallel
        const [processesRes, summaryRes] = await Promise.all([
          api.get(`/api/processes/${deviceId}/latest`),
          api.get(`/api/processes/${deviceId}/summary`),
        ]);

        const newProcesses = processesRes.data.processes || [];
        const newSummary = summaryRes.data;

        setProcesses(newProcesses);
        setSummary(newSummary);

        // Cache in localStorage to persist across sessions and navigation
        localStorage.setItem(cacheKey, JSON.stringify(newProcesses));
        localStorage.setItem(summaryCacheKey, JSON.stringify(newSummary));
      } catch (err: any) {
        console.error("Failed to fetch processes:", err);
        setError(err.response?.data?.detail || "Failed to load process data");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    // Refresh every 10 seconds
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [deviceId, cacheKey, summaryCacheKey]);

  // Get unique usernames
  const uniqueUsers = Array.from(new Set(processes.map((p) => p.username)));

  // Filter and sort processes
  const filteredProcesses = processes
    .filter((proc) => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        return (
          proc.name.toLowerCase().includes(query) ||
          proc.username.toLowerCase().includes(query) ||
          proc.pid.toString().includes(query) ||
          (proc.cmdline && proc.cmdline.toLowerCase().includes(query))
        );
      }
      return true;
    })
    .filter((proc) => {
      // User filter
      if (filterUser !== "all" && proc.username !== filterUser) return false;
      // Status filter
      if (filterStatus !== "all" && proc.status !== filterStatus) return false;
      return true;
    })
    .sort((a, b) => {
      switch (sortBy) {
        case "cpu":
          return (b.cpu_percent || 0) - (a.cpu_percent || 0);
        case "memory":
          return (b.memory_percent || 0) - (a.memory_percent || 0);
        case "pid":
          return a.pid - b.pid;
        case "name":
          return a.name.localeCompare(b.name);
        default:
          return 0;
      }
    });

  // Format bytes
  const formatBytes = (bytes: number | null) => {
    if (bytes === null) return "N/A";
    const mb = bytes / 1024 / 1024;
    return `${mb.toFixed(1)} MB`;
  };

  // Format percentage
  const formatPercent = (percent: number | null) => {
    if (percent === null) return "N/A";
    return `${percent.toFixed(1)}%`;
  };

  return (
    <div className="container mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/"
          className="text-sm text-blue-600 hover:text-blue-800 hover:underline mb-2 inline-block"
        >
          ← Back to Dashboard
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              Process Monitor
            </h1>
            <p className="text-gray-600 mt-1">
              Device: {deviceId?.substring(0, 8)}...
            </p>
          </div>
          {summary && (
            <div className="text-sm text-gray-500">
              Last updated:{" "}
              {new Date(summary.collected_at).toLocaleTimeString()}
            </div>
          )}
        </div>
      </div>

      {loading && !processes.length ? (
        <div className="flex items-center justify-center h-64">
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
            <p className="mt-4 text-gray-600">Loading processes...</p>
          </div>
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <p className="text-red-600">{error}</p>
        </div>
      ) : (
        <>
          {/* Summary Cards */}
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-white rounded-lg shadow-md border border-gray-200 p-4">
                <div className="text-sm font-medium text-gray-600">
                  Total Processes
                </div>
                <div className="text-3xl font-bold text-gray-900 mt-2">
                  {summary.total_processes}
                </div>
              </div>
              <div className="bg-white rounded-lg shadow-md border border-gray-200 p-4">
                <div className="text-sm font-medium text-gray-600">
                  CPU Utilization
                </div>
                <div className="text-3xl font-bold text-blue-600 mt-2">
                  {summary.system_cpu_percent !== undefined
                    ? summary.system_cpu_percent.toFixed(1)
                    : summary.cpu_utilization_percent?.toFixed(1) || "0.0"}
                  %
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {summary.cpu_count || 0} cores
                  {summary.system_cpu_percent !== undefined &&
                    ` • System metric`}
                  {summary.system_cpu_percent === undefined &&
                    ` • ${
                      summary.total_cpu_percent?.toFixed(1) || "0.0"
                    }% from processes`}
                </div>
              </div>
              <div className="bg-white rounded-lg shadow-md border border-gray-200 p-4">
                <div className="text-sm font-medium text-gray-600">
                  Total Memory Usage
                </div>
                <div className="text-3xl font-bold text-green-600 mt-2">
                  {summary.total_memory_percent?.toFixed(1) || "0.0"}%
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Avg: {summary.avg_memory_percent.toFixed(1)}% per process
                </div>
              </div>
              <div className="bg-white rounded-lg shadow-md border border-gray-200 p-4">
                <div className="text-sm font-medium text-gray-600">
                  Total Memory RSS
                </div>
                <div className="text-3xl font-bold text-purple-600 mt-2">
                  {summary.total_memory_rss_mb.toFixed(0)} MB
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {(summary.total_memory_rss_mb / 1024).toFixed(1)} GB
                </div>
              </div>
            </div>
          )}

          {/* Filters */}
          <div className="bg-white rounded-lg shadow-md border border-gray-200 p-4 mb-6">
            <div className="flex flex-wrap gap-4">
              <div className="flex-1 min-w-[200px]">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Search
                </label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by name, user, PID..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  User
                </label>
                <select
                  value={filterUser}
                  onChange={(e) => setFilterUser(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Users</option>
                  {uniqueUsers.map((user) => (
                    <option key={user} value={user}>
                      {user}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Sort By
                </label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="px-3 py-2 border border-gray-300 rounded-md text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="cpu">CPU %</option>
                  <option value="memory">Memory %</option>
                  <option value="pid">PID</option>
                  <option value="name">Name</option>
                </select>
              </div>
            </div>
            <div className="mt-3 text-sm text-gray-600">
              Showing {filteredProcesses.length} of {processes.length} processes
            </div>
          </div>

          {/* Process Table */}
          <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                      PID
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                      Name
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                      User
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                      CPU %
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                      Memory %
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                      RSS
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                      Threads
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredProcesses.length === 0 ? (
                    <tr>
                      <td
                        colSpan={8}
                        className="px-4 py-8 text-center text-gray-500"
                      >
                        No processes match your filters
                      </td>
                    </tr>
                  ) : (
                    filteredProcesses.map((proc) => (
                      <tr
                        key={proc.id}
                        onClick={() => setSelectedProcess(proc)}
                        className="hover:bg-gray-50 cursor-pointer transition-colors"
                      >
                        <td className="px-4 py-3 text-sm text-gray-900 font-mono">
                          {proc.pid}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-900 font-medium">
                          {proc.name}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {proc.username}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span
                            className={`font-medium ${
                              (proc.cpu_percent || 0) > 50
                                ? "text-red-600"
                                : (proc.cpu_percent || 0) > 20
                                ? "text-orange-600"
                                : "text-gray-900"
                            }`}
                          >
                            {formatPercent(proc.cpu_percent)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span
                            className={`font-medium ${
                              (proc.memory_percent || 0) > 10
                                ? "text-red-600"
                                : (proc.memory_percent || 0) > 5
                                ? "text-orange-600"
                                : "text-gray-900"
                            }`}
                          >
                            {formatPercent(proc.memory_percent)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 font-mono">
                          {formatBytes(proc.memory_rss)}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {proc.num_threads || 0}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span
                            className={`px-2 py-1 text-xs font-semibold rounded-full ${
                              proc.status === "running"
                                ? "bg-green-100 text-green-800"
                                : proc.status === "sleeping"
                                ? "bg-blue-100 text-blue-800"
                                : "bg-gray-100 text-gray-800"
                            }`}
                          >
                            {proc.status}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Process Details Modal */}
      {selectedProcess && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
          onClick={() => setSelectedProcess(null)}
        >
          <div
            className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">
                Process Details: {selectedProcess.name} (PID:{" "}
                {selectedProcess.pid})
              </h2>
              <button
                onClick={() => setSelectedProcess(null)}
                className="text-gray-400 hover:text-gray-600"
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

            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    PID
                  </label>
                  <p className="text-sm text-gray-900 mt-1 font-mono">
                    {selectedProcess.pid}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Parent PID
                  </label>
                  <p className="text-sm text-gray-900 mt-1 font-mono">
                    {selectedProcess.ppid || "N/A"}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    User
                  </label>
                  <p className="text-sm text-gray-900 mt-1">
                    {selectedProcess.username}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Status
                  </label>
                  <p className="text-sm text-gray-900 mt-1 capitalize">
                    {selectedProcess.status}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    CPU Usage
                  </label>
                  <p className="text-sm text-gray-900 mt-1 font-medium">
                    {formatPercent(selectedProcess.cpu_percent)}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Memory Usage
                  </label>
                  <p className="text-sm text-gray-900 mt-1 font-medium">
                    {formatPercent(selectedProcess.memory_percent)}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    RSS Memory
                  </label>
                  <p className="text-sm text-gray-900 mt-1 font-mono">
                    {formatBytes(selectedProcess.memory_rss)}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    VMS Memory
                  </label>
                  <p className="text-sm text-gray-900 mt-1 font-mono">
                    {formatBytes(selectedProcess.memory_vms)}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Threads
                  </label>
                  <p className="text-sm text-gray-900 mt-1">
                    {selectedProcess.num_threads || 0}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    File Descriptors
                  </label>
                  <p className="text-sm text-gray-900 mt-1">
                    {selectedProcess.num_fds || 0}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Network Connections
                  </label>
                  <p className="text-sm text-gray-900 mt-1">
                    {selectedProcess.num_connections || 0}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Created
                  </label>
                  <p className="text-sm text-gray-900 mt-1">
                    {selectedProcess.create_time
                      ? new Date(selectedProcess.create_time).toLocaleString()
                      : "N/A"}
                  </p>
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-500">
                  Executable Path
                </label>
                <p className="text-sm text-gray-900 mt-1 font-mono break-all bg-gray-50 p-2 rounded">
                  {selectedProcess.exe || "N/A"}
                </p>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-500">
                  Command Line
                </label>
                <p className="text-sm text-gray-900 mt-1 font-mono break-all bg-gray-50 p-2 rounded">
                  {selectedProcess.cmdline || "N/A"}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProcessesPage;
