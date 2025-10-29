import React, { useState, useEffect } from "react";
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
}

interface DeviceCommandsProps {
  agentId: string;
}

const DeviceCommands: React.FC<DeviceCommandsProps> = ({ agentId }) => {
  const [commands, setCommands] = useState<Command[]>([]);
  const [loading, setLoading] = useState(true);
  const [limit, setLimit] = useState(20);

  useEffect(() => {
    const fetchCommands = async () => {
      setLoading(true);
      try {
        const response = await api.get("/api/commands", {
          params: { agent_id: agentId, limit },
        });
        setCommands(response.data);
      } catch (err) {
        console.error("Error fetching commands:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchCommands();
  }, [agentId, limit]);

  const getCommandSeverity = (
    command: string
  ): "critical" | "high" | "medium" | "normal" => {
    const cmd = command.toLowerCase();

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

    if (
      cmd.includes("git push") ||
      cmd.includes("docker") ||
      cmd.includes("systemctl")
    ) {
      return "medium";
    }

    return "normal";
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
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return "just now";
  };

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="animate-pulse space-y-2">
          <div className="h-4 bg-gray-700 rounded w-3/4"></div>
          <div className="h-4 bg-gray-700 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (commands.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 text-center">
        <p className="text-gray-400">No commands recorded yet</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden">
      <div className="p-4 border-b border-gray-700 flex justify-between items-center">
        <h3 className="text-lg font-semibold text-white">Recent Commands</h3>
        <select
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="bg-gray-700 text-white px-3 py-1 rounded text-sm border border-gray-600 focus:outline-none focus:border-blue-500"
        >
          <option value={10}>Last 10</option>
          <option value={20}>Last 20</option>
          <option value={50}>Last 50</option>
          <option value={100}>Last 100</option>
        </select>
      </div>

      <div className="divide-y divide-gray-700 max-h-96 overflow-y-auto">
        {commands.map((cmd) => {
          const severity = getCommandSeverity(cmd.command);
          return (
            <div
              key={cmd.id}
              className="p-3 hover:bg-gray-750 transition-colors"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span
                      className={`px-2 py-0.5 text-xs font-medium rounded border ${getSeverityBadge(
                        severity
                      )}`}
                    >
                      {severity}
                    </span>
                    <span className="text-sm font-medium text-white">
                      {cmd.user_name}
                    </span>
                    {cmd.shell && (
                      <span className="text-xs text-gray-400">{cmd.shell}</span>
                    )}
                  </div>
                  <code className="block text-xs bg-gray-900 p-2 rounded font-mono text-gray-300 break-all">
                    {cmd.command}
                  </code>
                  {cmd.working_directory && (
                    <div className="mt-1 text-xs text-gray-500 flex items-center gap-1">
                      <svg
                        className="w-3 h-3"
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
                      <span className="truncate">{cmd.working_directory}</span>
                    </div>
                  )}
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-xs text-gray-400 whitespace-nowrap">
                    {formatTimestamp(cmd.timestamp)}
                  </div>
                  {cmd.exit_code !== null && (
                    <div
                      className={`text-xs mt-1 ${
                        cmd.exit_code === 0 ? "text-green-400" : "text-red-400"
                      }`}
                    >
                      Exit: {cmd.exit_code}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default DeviceCommands;
