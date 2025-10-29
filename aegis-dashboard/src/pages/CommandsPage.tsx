import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";

interface Command {
  id: number;
  command: string;
  user_name: string;
  timestamp: string;
  shell: string | null;
  source: string | null;
  working_directory: string | null;
  exit_code: number | null;
  agent_id: string;
  created_at: string;
}

interface Device {
  id: number;
  agent_id: string;
  hostname: string;
  status: string;
}

const CommandsPage: React.FC = () => {
  const { agentId } = useParams<{ agentId?: string }>();

  const [commands, setCommands] = useState<Command[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>(
    agentId || "all"
  );
  const [selectedUser, setSelectedUser] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch devices
  useEffect(() => {
    const fetchDevices = async () => {
      try {
        // Refresh device statuses first
        try {
          await api.post("/api/devices/refresh-status");
        } catch (err) {
          console.error("Failed to refresh device statuses:", err);
        }

        const response = await api.get("/api/devices");
        setDevices(response.data);
      } catch (err) {
        console.error("Error fetching devices:", err);
      }
    };
    fetchDevices();
  }, []);

  // Fetch commands
  useEffect(() => {
    const fetchCommands = async () => {
      setLoading(true);
      setError(null);

      try {
        const params: any = { limit: 100 };

        if (selectedDevice !== "all") {
          params.agent_id = selectedDevice;
        }

        if (selectedUser !== "all") {
          params.user_name = selectedUser;
        }

        const response = await api.get("/api/commands", { params });
        setCommands(response.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || "Failed to fetch commands");
        console.error("Error fetching commands:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchCommands();
  }, [selectedDevice, selectedUser]);

  // Get unique users from commands
  const uniqueUsers = Array.from(new Set(commands.map((cmd) => cmd.user_name)));

  // Filter commands by search query
  const filteredCommands = commands.filter(
    (cmd) =>
      cmd.command.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cmd.user_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cmd.working_directory?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Categorize command severity
  const getCommandSeverity = (command: string): string => {
    const cmd = command.toLowerCase();

    // Critical commands
    if (
      cmd.includes("rm -rf") ||
      cmd.includes("dd if=") ||
      cmd.includes("mkfs") ||
      cmd.includes("shred") ||
      cmd.includes("nc -lvp") ||
      cmd.includes("nc -l")
    ) {
      return "critical";
    }

    // High severity
    if (
      cmd.includes("sudo") ||
      cmd.includes("chmod 777") ||
      cmd.includes("nmap") ||
      (cmd.includes("curl") &&
        (cmd.includes(" -X POST") || cmd.includes(" -d "))) ||
      cmd.includes("wget") ||
      (cmd.includes("ssh") && cmd.includes("@"))
    ) {
      return "high";
    }

    // Medium severity
    if (
      cmd.includes("git push") ||
      cmd.includes("docker") ||
      cmd.includes("systemctl")
    ) {
      return "medium";
    }

    return "normal";
  };

  const getSeverityColor = (severity: string): string => {
    switch (severity) {
      case "critical":
        return "text-red-600 bg-red-50 border-red-200";
      case "high":
        return "text-orange-600 bg-orange-50 border-orange-200";
      case "medium":
        return "text-yellow-600 bg-yellow-50 border-yellow-200";
      default:
        return "text-gray-600 bg-gray-50 border-gray-200";
    }
  };

  const getSeverityBadge = (severity: string): string => {
    switch (severity) {
      case "critical":
        return "bg-red-100 text-red-800 border-red-300";
      case "high":
        return "bg-orange-100 text-orange-800 border-orange-300";
      case "medium":
        return "bg-yellow-100 text-yellow-800 border-yellow-300";
      default:
        return "bg-gray-100 text-gray-800 border-gray-300";
    }
  };

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  return (
    <div className="p-6">
      <Link
        to="/"
        className="text-sm text-blue-600 hover:text-blue-800 hover:underline mb-4 inline-block"
      >
        ← Back to Dashboard
      </Link>

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          Terminal Command History
        </h1>
        <p className="text-gray-600 mt-1">
          Monitor and analyze shell commands executed across your devices
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Device Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Device
            </label>
            <select
              value={selectedDevice}
              onChange={(e) => setSelectedDevice(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Devices</option>
              {devices.map((device) => (
                <option key={device.agent_id} value={device.agent_id}>
                  {device.hostname}
                </option>
              ))}
            </select>
          </div>

          {/* User Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              User
            </label>
            <select
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Users</option>
              {uniqueUsers.map((user) => (
                <option key={user} value={user}>
                  {user}
                </option>
              ))}
            </select>
          </div>

          {/* Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Search
            </label>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search commands..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 bg-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Total Commands</div>
          <div className="text-2xl font-bold text-gray-900">
            {filteredCommands.length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Critical</div>
          <div className="text-2xl font-bold text-red-600">
            {
              filteredCommands.filter(
                (cmd) => getCommandSeverity(cmd.command) === "critical"
              ).length
            }
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">High Risk</div>
          <div className="text-2xl font-bold text-orange-600">
            {
              filteredCommands.filter(
                (cmd) => getCommandSeverity(cmd.command) === "high"
              ).length
            }
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Unique Users</div>
          <div className="text-2xl font-bold text-gray-900">
            {uniqueUsers.length}
          </div>
        </div>
      </div>

      {/* Command List */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-4 py-3 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Commands</h2>
        </div>

        {loading ? (
          <div className="p-8 text-center text-gray-500">
            Loading commands...
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-600">{error}</div>
        ) : filteredCommands.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No commands found</div>
        ) : (
          <div className="divide-y divide-gray-200">
            {filteredCommands.map((cmd) => {
              const severity = getCommandSeverity(cmd.command);
              return (
                <div
                  key={cmd.id}
                  className={`p-4 hover:bg-gray-50 transition-colors border-l-4 ${getSeverityColor(
                    severity
                  )}`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className={`px-2 py-1 text-xs font-medium rounded border ${getSeverityBadge(
                            severity
                          )}`}
                        >
                          {severity.toUpperCase()}
                        </span>
                        <span className="text-sm font-medium text-gray-900">
                          {cmd.user_name}
                        </span>
                        <span className="text-sm text-gray-500">
                          {cmd.shell && `(${cmd.shell})`}
                        </span>
                      </div>
                      <code className="block text-sm bg-gray-100 p-2 rounded font-mono break-all">
                        {cmd.command}
                      </code>
                    </div>
                    <div className="ml-4 text-right">
                      <div className="text-xs text-gray-500">
                        {formatTimestamp(cmd.timestamp)}
                      </div>
                      {cmd.exit_code !== null && (
                        <div
                          className={`text-xs mt-1 ${
                            cmd.exit_code === 0
                              ? "text-green-600"
                              : "text-red-600"
                          }`}
                        >
                          Exit: {cmd.exit_code}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-4 text-xs text-gray-500 mt-2">
                    {cmd.working_directory && (
                      <div className="flex items-center gap-1">
                        <svg
                          className="w-4 h-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                          />
                        </svg>
                        <span>{cmd.working_directory}</span>
                      </div>
                    )}
                    {cmd.source && (
                      <div className="flex items-center gap-1">
                        <svg
                          className="w-4 h-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                        <span>Source: {cmd.source}</span>
                      </div>
                    )}
                    <div className="flex items-center gap-1">
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                        />
                      </svg>
                      <span>
                        {devices.find((d) => d.agent_id === cmd.agent_id)
                          ?.hostname || cmd.agent_id.substring(0, 8)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default CommandsPage;
