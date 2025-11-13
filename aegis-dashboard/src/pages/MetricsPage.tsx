import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useWebSocket } from "../hooks/useWebSocket";
import { api } from "../lib/api";

interface Metrics {
  cpu: {
    cpu_percent: number;
    load_avg: number[];
  };
  memory: {
    memory_percent: number;
    memory_available: number;
    memory_total: number;
  };
  disk: {
    disk_percent: number;
    disk_free: number;
    disk_total: number;
  };
  network: {
    net_bytes_sent: number;
    net_bytes_recv: number;
  };
  timestamp: number;
}

interface MetricsSeries {
  time: string;
  cpu: number;
  memory: number;
  disk: number;
  network_in: number;
  network_out: number;
}

// Custom tooltip components for better formatting
const CustomTooltip = ({ active, payload, label, unit = "%" }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-3 border border-gray-300 rounded shadow-lg">
        <p className="text-sm text-gray-600">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p
            key={index}
            className="text-sm font-semibold"
            style={{ color: entry.color }}
          >
            {entry.name}:{" "}
            {typeof entry.value === "number"
              ? entry.value.toFixed(2)
              : entry.value}
            {unit}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

const NetworkTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-3 border border-gray-300 rounded shadow-lg">
        <p className="text-sm text-gray-600">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p
            key={index}
            className="text-sm font-semibold"
            style={{ color: entry.color }}
          >
            {entry.name}:{" "}
            {typeof entry.value === "number"
              ? entry.value.toFixed(2)
              : entry.value}{" "}
            KB/s
          </p>
        ))}
      </div>
    );
  }
  return null;
};

const MetricsPage: React.FC = () => {
  const { deviceId } = useParams<{ deviceId: string }>();
  const [metricsHistory, setMetricsHistory] = useState<MetricsSeries[]>([]);
  const [lastMetrics, setLastMetrics] = useState<Metrics | null>(null);

  useEffect(() => {
    // Fetch historical metrics when component mounts
    const fetchMetrics = async () => {
      try {
        const response = await api.get(`/api/metrics/${deviceId}?timespan=1h`);
        // Transform the data for charts
        const series = response.data.map((m: Metrics) => ({
          time: new Date(m.timestamp * 1000).toLocaleTimeString(),
          cpu: m.cpu.cpu_percent,
          memory: m.memory.memory_percent,
          disk: m.disk.disk_percent,
          // Use rates (KB/s) if available, otherwise fall back to cumulative MB
          network_in:
            m.network.net_bytes_recv_rate !== undefined
              ? m.network.net_bytes_recv_rate / 1024 // Convert to KB/s
              : m.network.net_bytes_recv / 1024 / 1024, // MB
          network_out:
            m.network.net_bytes_sent_rate !== undefined
              ? m.network.net_bytes_sent_rate / 1024 // Convert to KB/s
              : m.network.net_bytes_sent / 1024 / 1024, // MB
        }));
        setMetricsHistory(series);

        // Set the most recent metric as lastMetrics for immediate display
        if (response.data.length > 0) {
          setLastMetrics(response.data[response.data.length - 1]);
        }
      } catch (error) {
        console.error("Failed to fetch metrics:", error);
      }
    };

    fetchMetrics();
  }, [deviceId]);

  // Handle real-time updates
  useWebSocket((data) => {
    if (data.type === "device_metrics" && data.payload.agent_id === deviceId) {
      const metrics: Metrics = data.payload.metrics;
      setLastMetrics(metrics);

      // Add to history
      setMetricsHistory((prev) => {
        const newPoint = {
          time: new Date().toLocaleTimeString(),
          cpu: metrics.cpu.cpu_percent,
          memory: metrics.memory.memory_percent,
          disk: metrics.disk.disk_percent,
          // Use rates (KB/s) if available, otherwise fall back to cumulative MB
          network_in:
            metrics.network.net_bytes_recv_rate !== undefined
              ? metrics.network.net_bytes_recv_rate / 1024 // Convert to KB/s
              : metrics.network.net_bytes_recv / 1024 / 1024, // MB
          network_out:
            metrics.network.net_bytes_sent_rate !== undefined
              ? metrics.network.net_bytes_sent_rate / 1024 // Convert to KB/s
              : metrics.network.net_bytes_sent / 1024 / 1024, // MB
        };

        // Keep last 60 points (1 hour at 1 point/minute)
        const newHistory = [...prev, newPoint].slice(-60);
        return newHistory;
      });
    }
  });

  return (
    <div className="p-4">
      <Link
        to="/"
        className="text-sm text-blue-600 hover:text-blue-800 hover:underline mb-4 inline-block"
      >
        ← Back to Dashboard
      </Link>

      <h1 className="text-2xl font-bold mb-4">Device Metrics</h1>

      {/* Current Values */}
      {lastMetrics && (
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-gray-500">CPU Usage</h3>
            <p className="text-2xl font-bold text-gray-900">
              {lastMetrics.cpu.cpu_percent.toFixed(1)}%
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-gray-500">Memory Usage</h3>
            <p className="text-2xl font-bold text-gray-900">
              {lastMetrics.memory.memory_percent.toFixed(1)}%
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-gray-500">Disk Usage</h3>
            <p className="text-2xl font-bold text-gray-900">
              {lastMetrics.disk.disk_percent.toFixed(1)}%
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-gray-500">Network I/O</h3>
            {lastMetrics.network.net_bytes_sent_rate !== undefined ? (
              <p className="text-sm text-gray-900">
                ↑ {(lastMetrics.network.net_bytes_sent_rate / 1024).toFixed(2)}{" "}
                KB/s
                <br />↓{" "}
                {(lastMetrics.network.net_bytes_recv_rate / 1024).toFixed(
                  2
                )}{" "}
                KB/s
              </p>
            ) : (
              <p className="text-sm text-gray-900">
                ↑{" "}
                {(lastMetrics.network.net_bytes_sent / 1024 / 1024).toFixed(2)}{" "}
                MB
                <br />↓{" "}
                {(lastMetrics.network.net_bytes_recv / 1024 / 1024).toFixed(
                  2
                )}{" "}
                MB
              </p>
            )}
          </div>
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-2 gap-4">
        {/* CPU Chart */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-gray-500 mb-4">CPU Usage Over Time</h3>
          <div className="h-64">
            {metricsHistory.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={metricsHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip content={<CustomTooltip unit="%" />} />
                  <Line
                    type="monotone"
                    dataKey="cpu"
                    stroke="#8884d8"
                    name="CPU Usage"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <svg
                    className="mx-auto h-12 w-12 text-gray-300"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                    />
                  </svg>
                  <p className="mt-2">Waiting for data...</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Memory Chart */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-gray-500 mb-4">Memory Usage Over Time</h3>
          <div className="h-64">
            {metricsHistory.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={metricsHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip content={<CustomTooltip unit="%" />} />
                  <Line
                    type="monotone"
                    dataKey="memory"
                    stroke="#82ca9d"
                    name="Memory Usage"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <svg
                    className="mx-auto h-12 w-12 text-gray-300"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
                    />
                  </svg>
                  <p className="mt-2">Waiting for data...</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Disk Chart */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-gray-500 mb-4">Disk Usage Over Time</h3>
          <div className="h-64">
            {metricsHistory.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={metricsHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip content={<CustomTooltip unit="%" />} />
                  <Line
                    type="monotone"
                    dataKey="disk"
                    stroke="#ffc658"
                    name="Disk Usage"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <svg
                    className="mx-auto h-12 w-12 text-gray-300"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"
                    />
                  </svg>
                  <p className="mt-2">Waiting for data...</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Network Chart */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-gray-500 mb-4">Network I/O Rate (KB/s)</h3>
          <div className="h-64">
            {metricsHistory.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={metricsHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip content={<NetworkTooltip />} />
                  <Line
                    type="monotone"
                    dataKey="network_in"
                    stroke="#8884d8"
                    name="Received"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="network_out"
                    stroke="#82ca9d"
                    name="Sent"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <svg
                    className="mx-auto h-12 w-12 text-gray-300"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                    />
                  </svg>
                  <p className="mt-2">Waiting for data...</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MetricsPage;
