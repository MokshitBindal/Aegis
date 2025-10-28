import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
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
          network_in: m.network.net_bytes_recv,
          network_out: m.network.net_bytes_sent,
        }));
        setMetricsHistory(series);
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
          network_in: metrics.network.net_bytes_recv,
          network_out: metrics.network.net_bytes_sent,
        };

        // Keep last 60 points (1 hour at 1 point/minute)
        const newHistory = [...prev, newPoint].slice(-60);
        return newHistory;
      });
    }
  });

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Device Metrics</h1>

      {/* Current Values */}
      {lastMetrics && (
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-gray-500">CPU Usage</h3>
            <p className="text-2xl font-bold">
              {lastMetrics.cpu.cpu_percent.toFixed(1)}%
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-gray-500">Memory Usage</h3>
            <p className="text-2xl font-bold">
              {lastMetrics.memory.memory_percent.toFixed(1)}%
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-gray-500">Disk Usage</h3>
            <p className="text-2xl font-bold">
              {lastMetrics.disk.disk_percent.toFixed(1)}%
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-gray-500">Network I/O</h3>
            <p className="text-sm">
              ↑ {(lastMetrics.network.net_bytes_sent / 1024 / 1024).toFixed(2)}{" "}
              MB
              <br />↓{" "}
              {(lastMetrics.network.net_bytes_recv / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-2 gap-4">
        {/* CPU Chart */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-gray-500 mb-4">CPU Usage Over Time</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={metricsHistory}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="cpu" stroke="#8884d8" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Memory Chart */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-gray-500 mb-4">Memory Usage Over Time</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={metricsHistory}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="memory" stroke="#82ca9d" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Disk Chart */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-gray-500 mb-4">Disk Usage Over Time</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={metricsHistory}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="disk" stroke="#ffc658" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Network Chart */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-gray-500 mb-4">Network I/O Over Time</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={metricsHistory}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="network_in"
                  stroke="#8884d8"
                  name="Received"
                />
                <Line
                  type="monotone"
                  dataKey="network_out"
                  stroke="#82ca9d"
                  name="Sent"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MetricsPage;
