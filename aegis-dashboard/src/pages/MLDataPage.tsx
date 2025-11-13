// src/pages/MLDataPage.tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

interface ExportStatus {
  logs_threshold: number;
  metrics_threshold: number;
  processes_threshold: number;
  commands_threshold: number;
  export_directory: string;
  last_export_counts: Record<string, number>;
  total_exports: number;
  last_export_time: string | null;
  unexported_logs: number;
  unexported_metrics: number;
  unexported_processes: number;
  unexported_commands: number;
}

interface ExportFile {
  type: string;
  filename: string;
  size_bytes: number;
  size_mb: number;
  row_count: number;
  last_modified: string;
}

type FileType = "logs" | "metrics" | "processes" | "commands";

export default function MLDataPage() {
  const { isOwner, isAdmin, token } = useAuth();
  const [status, setStatus] = useState<ExportStatus | null>(null);
  const [files, setFiles] = useState<ExportFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [selectedFileType, setSelectedFileType] = useState<FileType>("logs");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [agentId, setAgentId] = useState("");

  useEffect(() => {
    // Wait for auth to load before checking permissions
    if (!token) {
      setLoading(true);
      return;
    }

    if (!isOwner && !isAdmin) {
      setError("Only owners and admins can access ML data.");
      setLoading(false);
      return;
    }

    fetchStatus();
    fetchFiles();

    // Auto-refresh unexported counts every 60 seconds
    const intervalId = setInterval(() => {
      fetchStatus();
    }, 60000); // 60 seconds

    // Cleanup interval on unmount
    return () => clearInterval(intervalId);
  }, [isOwner, isAdmin, token]);

  const fetchStatus = async () => {
    try {
      const response = await api.get("/api/ml-data/status");
      setStatus(response.data);
    } catch (err: any) {
      console.error("Failed to fetch export status:", err);
      setError(err.response?.data?.detail || "Failed to load export status");
    }
  };

  const fetchFiles = async () => {
    try {
      const response = await api.get("/api/ml-data/exports");
      setFiles(response.data.exports);
    } catch (err: any) {
      console.error("Failed to fetch export files:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleManualExport = async () => {
    setExporting(true);
    try {
      await api.post("/api/ml-data/export/manual");
      alert("Export triggered successfully!");
      await fetchStatus();
      await fetchFiles();
    } catch (err: any) {
      console.error("Failed to trigger export:", err);
      alert(err.response?.data?.detail || "Failed to trigger export");
    } finally {
      setExporting(false);
    }
  };

  const handleDownload = async () => {
    try {
      // Build query parameters
      const params = new URLSearchParams();
      if (startDate)
        params.append("start_date", new Date(startDate).toISOString());
      if (endDate) params.append("end_date", new Date(endDate).toISOString());
      if (agentId) params.append("agent_id", agentId);

      const url = `/api/ml-data/download/${selectedFileType}?${params.toString()}`;

      // Get the token for download
      const token = localStorage.getItem("token");

      // Create a temporary link to trigger download
      const link = document.createElement("a");
      link.href = `${
        import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
      }${url}`;
      link.setAttribute("download", "");

      // Add authorization header via fetch and create blob
      const response = await fetch(link.href, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Download failed");
      }

      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);

      // Get filename from content-disposition header or use default
      const contentDisposition = response.headers.get("content-disposition");
      let filename = `${selectedFileType}.csv`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err: any) {
      console.error("Failed to download file:", err);
      alert("Failed to download file. Please try again.");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="flex items-center gap-3 text-gray-300">
          <svg
            className="animate-spin h-8 w-8"
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
          <span>Loading ML data...</span>
        </div>
      </div>
    );
  }

  if (error || (!isOwner && !isAdmin)) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="text-center text-red-400">
          <p className="text-xl font-semibold mb-2">Access Denied</p>
          <p>{error || "Only owners and admins can access this page."}</p>
          <Link
            to="/"
            className="text-blue-400 hover:underline mt-4 inline-block"
          >
            Go back to dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/"
          className="text-blue-400 hover:underline mb-4 inline-block"
        >
          ← Back to Dashboard
        </Link>
        <h1 className="text-3xl font-bold mb-2">ML Data Export</h1>
        <p className="text-gray-400">
          Download exported data for machine learning model training
        </p>
      </div>

      {/* Export Status */}
      {status && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {/* Unexported Logs */}
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-gray-400 text-sm">Unexported Logs</h3>
              <span
                className={`text-xs px-2 py-1 rounded ${
                  status.unexported_logs >= status.logs_threshold
                    ? "bg-yellow-600 text-yellow-100"
                    : "bg-gray-700 text-gray-300"
                }`}
              >
                {status.unexported_logs >= status.logs_threshold
                  ? "Ready"
                  : "Collecting"}
              </span>
            </div>
            <p className="text-2xl font-bold">
              {status.unexported_logs.toLocaleString()}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Threshold: {status.logs_threshold.toLocaleString()}
            </p>
          </div>

          {/* Unexported Metrics */}
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-gray-400 text-sm">Unexported Metrics</h3>
              <span
                className={`text-xs px-2 py-1 rounded ${
                  status.unexported_metrics >= status.metrics_threshold
                    ? "bg-yellow-600 text-yellow-100"
                    : "bg-gray-700 text-gray-300"
                }`}
              >
                {status.unexported_metrics >= status.metrics_threshold
                  ? "Ready"
                  : "Collecting"}
              </span>
            </div>
            <p className="text-2xl font-bold">
              {status.unexported_metrics.toLocaleString()}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Threshold: {status.metrics_threshold.toLocaleString()}
            </p>
          </div>

          {/* Unexported Processes */}
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-gray-400 text-sm">Unexported Processes</h3>
              <span
                className={`text-xs px-2 py-1 rounded ${
                  status.unexported_processes >= status.processes_threshold
                    ? "bg-yellow-600 text-yellow-100"
                    : "bg-gray-700 text-gray-300"
                }`}
              >
                {status.unexported_processes >= status.processes_threshold
                  ? "Ready"
                  : "Collecting"}
              </span>
            </div>
            <p className="text-2xl font-bold">
              {status.unexported_processes.toLocaleString()}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Threshold: {status.processes_threshold.toLocaleString()}
            </p>
          </div>

          {/* Unexported Commands */}
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-gray-400 text-sm">Unexported Commands</h3>
              <span
                className={`text-xs px-2 py-1 rounded ${
                  status.unexported_commands >= status.commands_threshold
                    ? "bg-yellow-600 text-yellow-100"
                    : "bg-gray-700 text-gray-300"
                }`}
              >
                {status.unexported_commands >= status.commands_threshold
                  ? "Ready"
                  : "Collecting"}
              </span>
            </div>
            <p className="text-2xl font-bold">
              {status.unexported_commands.toLocaleString()}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Threshold: {status.commands_threshold.toLocaleString()}
            </p>
          </div>
        </div>
      )}

      {/* Exported Files Summary */}
      {status && (
        <div className="bg-gray-800 rounded-lg p-6 mb-6 border border-gray-700">
          <h2 className="text-xl font-semibold mb-4">Exported Files Summary</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-gray-400 text-sm">Total Exported Rows</p>
              <p className="text-3xl font-bold text-green-400">
                {status.total_exports.toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-gray-400 text-sm">Last Export</p>
              <p className="text-lg">
                {status.last_export_time
                  ? new Date(status.last_export_time).toLocaleString()
                  : "Never"}
              </p>
            </div>
            <div>
              <p className="text-gray-400 text-sm">Export Directory</p>
              <p className="text-sm text-gray-300 font-mono">
                {status.export_directory}
              </p>
            </div>
          </div>
          <div className="mt-4">
            <button
              onClick={handleManualExport}
              disabled={exporting}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
            >
              {exporting ? (
                <>
                  <svg
                    className="animate-spin inline h-4 w-4 mr-2"
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
                  Exporting...
                </>
              ) : (
                "Trigger Manual Export"
              )}
            </button>
          </div>
        </div>
      )}

      {/* Download Section */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6 border border-gray-700">
        <h2 className="text-xl font-semibold mb-4">Download Data</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {/* File Type */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Data Type
            </label>
            <select
              value={selectedFileType}
              onChange={(e) => setSelectedFileType(e.target.value as FileType)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="logs">Logs</option>
              <option value="metrics">Metrics</option>
              <option value="processes">Processes</option>
              <option value="commands">Commands</option>
            </select>
          </div>

          {/* Agent ID */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Agent ID (optional)
            </label>
            <input
              type="text"
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              placeholder="Filter by specific agent"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Start Date */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Start Date (optional)
            </label>
            <input
              type="datetime-local"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* End Date */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              End Date (optional)
            </label>
            <input
              type="datetime-local"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <button
          onClick={handleDownload}
          className="px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors font-medium"
        >
          Download {selectedFileType}.csv
        </button>

        {(startDate || endDate || agentId) && (
          <p className="text-sm text-gray-400 mt-2">
            Note: Applying filters will create a custom CSV file with only the
            selected data.
          </p>
        )}
      </div>

      {/* Available Files Table */}
      <div className="bg-gray-800 rounded-lg overflow-hidden border border-gray-700">
        <div className="px-6 py-4 border-b border-gray-700">
          <h2 className="text-xl font-semibold">Available Export Files</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-700">
            <thead className="bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  File Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Filename
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Rows
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Size
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Last Modified
                </th>
              </tr>
            </thead>
            <tbody className="bg-gray-800 divide-y divide-gray-700">
              {files.length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-6 py-8 text-center text-gray-400"
                  >
                    No export files available yet. Trigger a manual export to
                    create files.
                  </td>
                </tr>
              ) : (
                files.map((file) => (
                  <tr key={file.filename} className="hover:bg-gray-750">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-semibold rounded bg-blue-600 text-blue-100">
                        {file.type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap font-mono text-sm">
                      {file.filename}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {file.row_count.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {file.size_mb.toFixed(2)} MB
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">
                      {new Date(file.last_modified).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
