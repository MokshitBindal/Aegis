// src/pages/UserManagementPage.tsx
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../lib/api";

interface User {
  id: number;
  email: string;
  role: string;
  is_active: boolean;
  created_by: number | null;
  last_login: string | null;
}

interface Device {
  id: number;
  agent_id: string;
  name: string;
  hostname: string;
  registered_at: string;
  user_id: number | null;
}

interface Assignment {
  assignment_id: number;
  user_id: number;
  user_email: string;
  user_role: string;
  assigned_at: string;
  assigned_by: string | null;
}

export default function UserManagementPage() {
  const { isOwner } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeviceModal, setShowDeviceModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [userAssignments, setUserAssignments] = useState<Assignment[]>([]);

  // Create user form
  const [newUserEmail, setNewUserEmail] = useState("");
  const [newUserPassword, setNewUserPassword] = useState("");
  const [newUserRole, setNewUserRole] = useState("device_user");

  // Edit user form
  const [editUserRole, setEditUserRole] = useState("");
  const [editUserActive, setEditUserActive] = useState(true);

  const [actionLoading, setActionLoading] = useState(false);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const [usersRes, devicesRes] = await Promise.all([
        api.get("/api/admin/users"),
        api.get("/api/devices"),
      ]);
      setUsers(usersRes.data);
      setDevices(devicesRes.data);
      setError(null);
    } catch (err: any) {
      console.error("Failed to fetch data:", err);
      setError(err.response?.data?.detail || "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOwner) {
      fetchUsers();
    }
  }, [isOwner]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);

    try {
      await api.post("/api/admin/users", {
        email: newUserEmail,
        password: newUserPassword,
        role: newUserRole,
      });
      setShowCreateModal(false);
      setNewUserEmail("");
      setNewUserPassword("");
      setNewUserRole("device_user");
      await fetchUsers();
      alert("User created successfully!");
    } catch (err: any) {
      console.error("Failed to create user:", err);
      alert(err.response?.data?.detail || "Failed to create user");
    } finally {
      setActionLoading(false);
    }
  };

  const handleOpenEditModal = (user: User) => {
    setSelectedUser(user);
    setEditUserRole(user.role);
    setEditUserActive(user.is_active);
    setShowEditModal(true);
  };

  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;

    setActionLoading(true);
    try {
      await api.put(`/api/admin/users/${selectedUser.id}`, {
        role: editUserRole,
        is_active: editUserActive,
      });
      setShowEditModal(false);
      await fetchUsers();
      alert("User updated successfully!");
    } catch (err: any) {
      console.error("Failed to update user:", err);
      alert(err.response?.data?.detail || "Failed to update user");
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteUser = async (userId: number, email: string) => {
    if (!confirm(`Are you sure you want to disable user ${email}?`)) return;

    setActionLoading(true);
    try {
      await api.delete(`/api/admin/users/${userId}`);
      await fetchUsers();
      alert("User disabled successfully!");
    } catch (err: any) {
      console.error("Failed to delete user:", err);
      alert(err.response?.data?.detail || "Failed to disable user");
    } finally {
      setActionLoading(false);
    }
  };

  // Device Assignment Functions
  const handleOpenDeviceModal = async (user: User) => {
    setSelectedUser(user);
    setShowDeviceModal(true);

    // Fetch assignments for this user
    try {
      // Get all assignments for each device and filter by user
      const assignmentPromises = devices.map((device) =>
        api
          .get(`/api/device/${device.id}/assignments`)
          .catch(() => ({ data: { assignments: [] } }))
      );
      const assignmentResults = await Promise.all(assignmentPromises);

      // Filter assignments for the selected user
      const userDeviceAssignments: Assignment[] = [];
      assignmentResults.forEach((result) => {
        const deviceAssignments = result.data.assignments.filter(
          (a: Assignment) => a.user_id === user.id
        );
        userDeviceAssignments.push(...deviceAssignments);
      });

      setUserAssignments(userDeviceAssignments);
    } catch (err) {
      console.error("Failed to fetch assignments:", err);
      setUserAssignments([]);
    }
  };

  const handleAssignDevice = async (deviceId: number) => {
    if (!selectedUser) return;

    try {
      setActionLoading(true);
      await api.post(
        `/api/device/assign?device_id=${deviceId}&user_id=${selectedUser.id}`
      );
      alert("Device assigned successfully!");
      await handleOpenDeviceModal(selectedUser); // Refresh assignments
    } catch (err: any) {
      console.error("Failed to assign device:", err);
      alert(err.response?.data?.detail || "Failed to assign device");
    } finally {
      setActionLoading(false);
    }
  };

  const handleUnassignDevice = async (deviceId: number) => {
    if (!selectedUser) return;

    if (!confirm("Are you sure you want to remove this device assignment?"))
      return;

    try {
      setActionLoading(true);
      await api.delete(
        `/api/device/${deviceId}/unassign?user_id=${selectedUser.id}`
      );
      alert("Device unassigned successfully!");
      await handleOpenDeviceModal(selectedUser); // Refresh assignments
    } catch (err: any) {
      console.error("Failed to unassign device:", err);
      alert(err.response?.data?.detail || "Failed to unassign device");
    } finally {
      setActionLoading(false);
    }
  };

  if (!isOwner) {
    return (
      <div className="container p-8 mx-auto">
        <div className="bg-red-900 text-white p-4 rounded-md">
          <p className="font-bold">Access Denied</p>
          <p>You don't have permission to access this page.</p>
          <Link
            to="/"
            className="text-blue-300 hover:underline mt-2 inline-block"
          >
            ← Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container p-8 mx-auto">
      <header className="flex items-center justify-between pb-4 border-b border-gray-700">
        <div>
          <Link to="/" className="text-blue-400 hover:underline text-sm">
            ← Back to Dashboard
          </Link>
          <h1 className="text-3xl font-bold mt-2">User Management</h1>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
        >
          + Create User
        </button>
      </header>

      <main className="mt-6">
        {loading && <p className="text-gray-400">Loading users...</p>}
        {error && <p className="text-red-400">{error}</p>}

        {!loading && !error && (
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-900">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">
                    Email
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">
                    Role
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">
                    Last Login
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">
                    Devices
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-750">
                    <td className="px-4 py-3 text-sm text-white">
                      {user.email}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span
                        className={`px-2 py-1 text-xs font-bold rounded ${
                          user.role === "owner"
                            ? "bg-purple-600"
                            : user.role === "admin"
                            ? "bg-yellow-600"
                            : "bg-blue-600"
                        }`}
                      >
                        {user.role.replace("_", " ").toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span
                        className={`px-2 py-1 text-xs font-bold rounded ${
                          user.is_active ? "bg-green-600" : "bg-red-600"
                        }`}
                      >
                        {user.is_active ? "ACTIVE" : "DISABLED"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-400">
                      {user.last_login
                        ? new Date(user.last_login).toLocaleString()
                        : "Never"}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {user.role !== "owner" && (
                        <button
                          onClick={() => handleOpenDeviceModal(user)}
                          className="px-3 py-1 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors text-xs"
                        >
                          Manage Devices
                        </button>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {user.role !== "owner" && (
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleOpenEditModal(user)}
                            className="px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-xs"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() =>
                              handleDeleteUser(user.id, user.email)
                            }
                            disabled={actionLoading}
                            className="px-3 py-1 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors text-xs disabled:bg-gray-600"
                          >
                            Disable
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      {/* Create User Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-lg max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">Create New User</h2>
            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Email *
                </label>
                <input
                  type="email"
                  value={newUserEmail}
                  onChange={(e) => setNewUserEmail(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-900 text-white rounded-md border border-gray-700"
                  placeholder="user@example.com"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  Password *
                </label>
                <input
                  type="password"
                  value={newUserPassword}
                  onChange={(e) => setNewUserPassword(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-900 text-white rounded-md border border-gray-700"
                  placeholder="••••••••"
                  required
                  minLength={8}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Role *</label>
                <select
                  value={newUserRole}
                  onChange={(e) => setNewUserRole(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-900 text-white rounded-md border border-gray-700"
                >
                  <option value="device_user">Device User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="flex gap-2 mt-6">
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="flex-1 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors disabled:bg-gray-600"
                >
                  {actionLoading ? "Creating..." : "Create User"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit User Modal */}
      {showEditModal && selectedUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-lg max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">
              Edit User: {selectedUser.email}
            </h2>
            <form onSubmit={handleUpdateUser} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Role *</label>
                <select
                  value={editUserRole}
                  onChange={(e) => setEditUserRole(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-900 text-white rounded-md border border-gray-700"
                >
                  <option value="device_user">Device User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={editUserActive}
                    onChange={(e) => setEditUserActive(e.target.checked)}
                    className="w-4 h-4"
                  />
                  <span className="text-sm font-medium">Account Active</span>
                </label>
              </div>
              <div className="flex gap-2 mt-6">
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:bg-gray-600"
                >
                  {actionLoading ? "Updating..." : "Update User"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Device Management Modal */}
      {showDeviceModal && selectedUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-bold">
                  Device Access: {selectedUser.email}
                </h2>
                <p className="text-sm text-gray-400 mt-1">
                  {selectedUser.role === "admin"
                    ? "Assign devices this admin can manage"
                    : "Assign devices this user can access"}
                </p>
              </div>
              <button
                onClick={() => setShowDeviceModal(false)}
                className="text-gray-400 hover:text-white transition-colors"
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

            {devices.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                <svg
                  className="mx-auto h-16 w-16 text-gray-600 mb-4"
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
                <p className="font-medium">No devices available</p>
                <p className="text-sm mt-1">
                  Register devices to assign them to users
                </p>
              </div>
            ) : (
              <div className="space-y-2 mt-4">
                {devices.map((device) => (
                  <DeviceRow
                    key={device.id}
                    device={device}
                    userId={selectedUser.id}
                    onAssign={() => handleAssignDevice(device.id)}
                    onUnassign={() => handleUnassignDevice(device.id)}
                    actionLoading={actionLoading}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Separate component for device row to manage its own assignment state
function DeviceRow({
  device,
  userId,
  onAssign,
  onUnassign,
  actionLoading,
}: {
  device: { id: number; name: string; hostname: string; agent_id: string };
  userId: number;
  onAssign: () => void;
  onUnassign: () => void;
  actionLoading: boolean;
}) {
  const [isAssigned, setIsAssigned] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const checkAssignment = async () => {
      try {
        const response = await api.get(`/api/device/${device.id}/assignments`);
        const assigned = response.data.assignments.some(
          (a: { user_id: number }) => a.user_id === userId
        );
        setIsAssigned(assigned);
      } catch (err) {
        console.error("Failed to check assignment:", err);
      } finally {
        setChecking(false);
      }
    };
    checkAssignment();
  }, [device.id, userId]);

  const handleToggle = async () => {
    if (isAssigned) {
      await onUnassign();
    } else {
      await onAssign();
    }
    // Refresh assignment status
    setChecking(true);
    try {
      const response = await api.get(`/api/device/${device.id}/assignments`);
      const assigned = response.data.assignments.some(
        (a: { user_id: number }) => a.user_id === userId
      );
      setIsAssigned(assigned);
    } catch (err) {
      console.error("Failed to refresh assignment:", err);
    } finally {
      setChecking(false);
    }
  };

  return (
    <div
      className={`flex items-center justify-between p-4 rounded-lg border-2 transition-colors ${
        isAssigned
          ? "bg-green-900 bg-opacity-20 border-green-600"
          : "bg-gray-900 border-gray-700 hover:border-gray-600"
      }`}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3">
          {isAssigned && (
            <svg
              className="w-5 h-5 text-green-500 flex-shrink-0"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
          )}
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-white truncate">{device.name}</p>
            <p className="text-sm text-gray-400 truncate">{device.hostname}</p>
            <p className="text-xs text-gray-500 font-mono truncate mt-1">
              {device.agent_id.substring(0, 24)}...
            </p>
          </div>
        </div>
      </div>

      <button
        onClick={handleToggle}
        disabled={actionLoading || checking}
        className={`ml-4 px-4 py-2 rounded-md font-medium text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
          isAssigned
            ? "bg-red-600 hover:bg-red-700 text-white"
            : "bg-green-600 hover:bg-green-700 text-white"
        }`}
      >
        {checking ? "..." : isAssigned ? "Remove Access" : "Grant Access"}
      </button>
    </div>
  );
}
