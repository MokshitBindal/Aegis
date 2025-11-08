// src/pages/UserManagementPage.tsx
import { useEffect, useState } from "react";
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

export default function UserManagementPage() {
  const { isOwner } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

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
      const response = await api.get("/api/admin/users");
      setUsers(response.data);
      setError(null);
    } catch (err: any) {
      console.error("Failed to fetch users:", err);
      setError(err.response?.data?.detail || "Failed to load users");
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
    </div>
  );
}
