import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../lib/api";

interface Device {
  id: number;
  agent_id: string;
  name: string;
  hostname: string;
  registered_at: string;
  user_id: number | null;
}

interface User {
  id: number;
  email: string;
  role: string;
}

interface Assignment {
  assignment_id: number;
  user_id: number;
  user_email: string;
  user_role: string;
  assigned_at: string;
  assigned_by: string | null;
}

const DeviceManagementPage: React.FC = () => {
  const { isOwner } = useAuth();
  const [devices, setDevices] = useState<Device[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch devices and users
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [devicesRes, usersRes] = await Promise.all([
          api.get("/api/devices"),
          api.get("/api/users"),
        ]);
        setDevices(devicesRes.data);
        setUsers(usersRes.data.filter((u: User) => u.role !== "owner"));
      } catch (err) {
        console.error("Failed to fetch data:", err);
        setError("Failed to load devices or users");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Fetch assignments for selected device
  const fetchAssignments = async (deviceId: number) => {
    try {
      const response = await api.get(`/api/device/${deviceId}/assignments`);
      setAssignments(response.data.assignments);
    } catch (err) {
      console.error("Failed to fetch assignments:", err);
      setAssignments([]);
    }
  };

  // Handle device selection
  const handleDeviceSelect = async (device: Device) => {
    setSelectedDevice(device);
    setSelectedUserId("");
    await fetchAssignments(device.id);
  };

  // Assign device to user
  const handleAssign = async () => {
    if (!selectedDevice || !selectedUserId) {
      alert("Please select both a device and a user");
      return;
    }

    try {
      setActionLoading(true);
      await api.post(
        `/api/device/assign?device_id=${selectedDevice.id}&user_id=${selectedUserId}`
      );
      alert("Device assigned successfully!");
      setSelectedUserId("");
      await fetchAssignments(selectedDevice.id);
    } catch (err: any) {
      console.error("Failed to assign device:", err);
      alert(
        err.response?.data?.detail ||
          "Failed to assign device. Please try again."
      );
    } finally {
      setActionLoading(false);
    }
  };

  // Unassign device from user
  const handleUnassign = async (userId: number) => {
    if (!selectedDevice) return;

    if (!confirm("Are you sure you want to remove this assignment?")) {
      return;
    }

    try {
      setActionLoading(true);
      await api.delete(
        `/api/device/${selectedDevice.id}/unassign?user_id=${userId}`
      );
      alert("Device unassigned successfully!");
      await fetchAssignments(selectedDevice.id);
    } catch (err: any) {
      console.error("Failed to unassign device:", err);
      alert(
        err.response?.data?.detail ||
          "Failed to unassign device. Please try again."
      );
    } finally {
      setActionLoading(false);
    }
  };

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  // Get role badge color
  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case "admin":
        return "bg-purple-100 text-purple-800 border-purple-200";
      case "device_user":
        return "bg-blue-100 text-blue-800 border-blue-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  if (!isOwner) {
    return (
      <div className="container mx-auto p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h2 className="text-2xl font-bold text-red-800 mb-2">
            Access Denied
          </h2>
          <p className="text-red-600">
            Only Owners can access device management.
          </p>
          <Link
            to="/"
            className="inline-block mt-4 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
          >
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-8">
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/"
          className="text-sm text-blue-600 hover:text-blue-800 hover:underline mb-2 inline-block"
        >
          ← Back to Dashboard
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">Device Management</h1>
        <p className="text-gray-600 mt-2">
          Assign devices to admins and users to grant them access
        </p>
      </div>

      {loading ? (
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
            <p className="mt-4 text-gray-600">Loading...</p>
          </div>
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <p className="text-red-600">{error}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Panel: Devices List */}
          <div className="bg-white rounded-lg shadow-md border border-gray-200">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">
                Devices ({devices.length})
              </h2>
            </div>
            <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
              {devices.length === 0 ? (
                <div className="p-6 text-center text-gray-500">
                  No devices registered yet
                </div>
              ) : (
                devices.map((device) => (
                  <button
                    key={device.id}
                    onClick={() => handleDeviceSelect(device)}
                    className={`w-full text-left p-4 hover:bg-gray-50 transition-colors ${
                      selectedDevice?.id === device.id
                        ? "bg-blue-50 border-l-4 border-blue-600"
                        : ""
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-gray-900">
                          {device.name}
                        </p>
                        <p className="text-sm text-gray-600">
                          {device.hostname}
                        </p>
                        <p className="text-xs text-gray-400 font-mono mt-1">
                          {device.agent_id.substring(0, 16)}...
                        </p>
                      </div>
                      {selectedDevice?.id === device.id && (
                        <svg
                          className="w-6 h-6 text-blue-600 flex-shrink-0 ml-2"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9 5l7 7-7 7"
                          />
                        </svg>
                      )}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Right Panel: Assignment Management */}
          <div className="bg-white rounded-lg shadow-md border border-gray-200">
            {selectedDevice ? (
              <>
                {/* Device Info Header */}
                <div className="p-4 border-b border-gray-200 bg-gray-50">
                  <h2 className="text-xl font-semibold text-gray-900">
                    {selectedDevice.name}
                  </h2>
                  <p className="text-sm text-gray-600 mt-1">
                    Manage user access for this device
                  </p>
                </div>

                {/* Assign New User Section */}
                <div className="p-4 border-b border-gray-200 bg-blue-50">
                  <h3 className="font-semibold text-gray-900 mb-3">
                    Assign New User
                  </h3>
                  <div className="flex gap-2">
                    <select
                      value={selectedUserId}
                      onChange={(e) => setSelectedUserId(e.target.value)}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                      disabled={actionLoading}
                    >
                      <option value="">Select a user...</option>
                      {users
                        .filter(
                          (user) =>
                            !assignments.some((a) => a.user_id === user.id)
                        )
                        .map((user) => (
                          <option key={user.id} value={user.id}>
                            {user.email} ({user.role.replace("_", " ")})
                          </option>
                        ))}
                    </select>
                    <button
                      onClick={handleAssign}
                      disabled={!selectedUserId || actionLoading}
                      className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed font-medium"
                    >
                      {actionLoading ? "..." : "Assign"}
                    </button>
                  </div>
                </div>

                {/* Current Assignments List */}
                <div className="p-4">
                  <h3 className="font-semibold text-gray-900 mb-3">
                    Current Assignments ({assignments.length})
                  </h3>
                  <div className="space-y-2 max-h-[400px] overflow-y-auto">
                    {assignments.length === 0 ? (
                      <div className="text-center py-6 text-gray-500">
                        <svg
                          className="mx-auto h-12 w-12 text-gray-300 mb-2"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                          />
                        </svg>
                        <p className="text-sm">
                          No users assigned to this device
                        </p>
                        <p className="text-xs text-gray-400 mt-1">
                          Use the form above to assign users
                        </p>
                      </div>
                    ) : (
                      assignments.map((assignment) => (
                        <div
                          key={assignment.assignment_id}
                          className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <p className="font-medium text-gray-900">
                                {assignment.user_email}
                              </p>
                              <span
                                className={`px-2 py-0.5 text-xs font-semibold rounded-md border ${getRoleBadgeColor(
                                  assignment.user_role
                                )}`}
                              >
                                {assignment.user_role.replace("_", " ")}
                              </span>
                            </div>
                            <p className="text-xs text-gray-500">
                              Assigned: {formatDate(assignment.assigned_at)}
                            </p>
                            {assignment.assigned_by && (
                              <p className="text-xs text-gray-400">
                                By: {assignment.assigned_by}
                              </p>
                            )}
                          </div>
                          <button
                            onClick={() => handleUnassign(assignment.user_id)}
                            disabled={actionLoading}
                            className="ml-3 px-3 py-1.5 text-sm bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
                          >
                            Remove
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-full p-8">
                <div className="text-center text-gray-400">
                  <svg
                    className="mx-auto h-16 w-16 text-gray-300 mb-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                    />
                  </svg>
                  <p className="text-lg font-medium">No device selected</p>
                  <p className="text-sm mt-1">
                    Select a device from the list to manage assignments
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default DeviceManagementPage;
