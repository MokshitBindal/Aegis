// src/pages/AlertTriagePage.tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../lib/api";

interface Alert {
  id: number;
  alert_id: number;
  agent_id: string;
  rule_name: string;
  severity: string;
  details: any;
  created_at: string;
  assignment_status: string;
  hostname?: string;
  // Legacy fields for backward compatibility
  alert_type?: string;
  message?: string;
  triggered_at?: string;
}

interface AlertAssignment {
  id: number;
  alert_id: number;
  assigned_to: number;
  assigned_at: string;
  status: string;
  notes: string | null;
  resolution: string | null;
  resolved_at: string | null;
  escalated_at: string | null;
  escalated_to: number | null;
  // Enriched fields from backend
  rule_name?: string;
  severity?: string;
  hostname?: string;
  agent_id?: string;
}

interface MyAssignmentsResponse {
  total: number;
  assignments: AlertAssignment[];
}

export default function AlertTriagePage() {
  const { isAdmin, isOwner } = useAuth();
  const [unassignedAlerts, setUnassignedAlerts] = useState<Alert[]>([]);
  const [myAssignments, setMyAssignments] = useState<AlertAssignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"unassigned" | "my-assignments">(
    "unassigned"
  );
  const [includeResolved, setIncludeResolved] = useState(true);

  // Modal states
  const [selectedAssignment, setSelectedAssignment] =
    useState<AlertAssignment | null>(null);
  const [showUpdateModal, setShowUpdateModal] = useState(false);
  const [showEscalateModal, setShowEscalateModal] = useState(false);
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState("investigating");
  const [resolution, setResolution] = useState("");
  const [escalationNotes, setEscalationNotes] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const fetchUnassignedAlerts = async () => {
    try {
      const response = await api.get("/api/alerts/unassigned", {
        params: { limit: 500 },
      });
      setUnassignedAlerts(response.data);
    } catch (err) {
      console.error("Failed to fetch unassigned alerts:", err);
      setError("Failed to load unassigned alerts");
    }
  };

  const fetchMyAssignments = async () => {
    try {
      const response = await api.get<MyAssignmentsResponse>(
        "/api/alerts/my-assignments",
        {
          params: { include_resolved: includeResolved },
        }
      );
      // Handle both old format (array) and new format (object with assignments array)
      const assignments = Array.isArray(response.data)
        ? response.data
        : response.data.assignments || [];
      setMyAssignments(assignments);
    } catch (err) {
      console.error("Failed to fetch my assignments:", err);
      setError("Failed to load assignments");
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      if (activeTab === "unassigned") {
        await fetchUnassignedAlerts();
      } else {
        await fetchMyAssignments();
      }
      setLoading(false);
    };
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [includeResolved, activeTab]);

  const handleClaimAlert = async (alertId: number) => {
    if (!isAdmin) return;

    setActionLoading(true);
    try {
      await api.post(`/api/alerts/${alertId}/claim`);
      // Refresh both lists
      await Promise.all([fetchUnassignedAlerts(), fetchMyAssignments()]);
      alert("Alert claimed successfully!");
    } catch (err: any) {
      console.error("Failed to claim alert:", err);
      alert(err.response?.data?.detail || "Failed to claim alert");
    } finally {
      setActionLoading(false);
    }
  };

  const handleOpenUpdateModal = (assignment: AlertAssignment) => {
    setSelectedAssignment(assignment);
    setNotes(assignment.notes || "");
    setStatus(assignment.status);
    setResolution(assignment.resolution || "");
    setShowUpdateModal(true);
  };

  const handleUpdateAssignment = async () => {
    if (!selectedAssignment) return;

    setActionLoading(true);
    try {
      await api.put(`/api/alerts/${selectedAssignment.alert_id}/status`, {
        status,
        notes,
        resolution: resolution || null,
      });
      setShowUpdateModal(false);
      await fetchMyAssignments();
      alert("Assignment updated successfully!");
    } catch (err: any) {
      console.error("Failed to update assignment:", err);
      alert(err.response?.data?.detail || "Failed to update assignment");
    } finally {
      setActionLoading(false);
    }
  };

  const handleOpenEscalateModal = (assignment: AlertAssignment) => {
    setSelectedAssignment(assignment);
    setEscalationNotes("");
    setShowEscalateModal(true);
  };

  const handleEscalateAlert = async () => {
    if (!selectedAssignment || !isAdmin) return;

    setActionLoading(true);
    try {
      await api.post(`/api/alerts/${selectedAssignment.alert_id}/escalate`, {
        notes: escalationNotes,
      });
      setShowEscalateModal(false);
      await fetchMyAssignments();
      alert("Alert escalated to Owner successfully!");
    } catch (err: any) {
      console.error("Failed to escalate alert:", err);
      alert(err.response?.data?.detail || "Failed to escalate alert");
    } finally {
      setActionLoading(false);
    }
  };

  if (!isAdmin && !isOwner) {
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
          <h1 className="text-3xl font-bold mt-2">Alert Triage</h1>
        </div>
      </header>

      {/* Tabs */}
      <div className="flex justify-between items-center mt-6 border-b border-gray-700">
        <div className="flex gap-4">
          <button
            onClick={() => setActiveTab("unassigned")}
            className={`px-4 py-2 font-medium transition-colors ${
              activeTab === "unassigned"
                ? "text-blue-400 border-b-2 border-blue-400"
                : "text-gray-400 hover:text-gray-300"
            }`}
          >
            Unassigned Alerts ({unassignedAlerts.length})
          </button>
          <button
            onClick={() => setActiveTab("my-assignments")}
            className={`px-4 py-2 font-medium transition-colors ${
              activeTab === "my-assignments"
                ? "text-blue-400 border-b-2 border-blue-400"
                : "text-gray-400 hover:text-gray-300"
            }`}
          >
            My Assignments ({myAssignments.length})
          </button>
        </div>

        {/* Show Resolved Toggle - only visible on my-assignments tab */}
        {activeTab === "my-assignments" && (
          <label className="flex items-center gap-2 pb-2 cursor-pointer">
            <input
              type="checkbox"
              checked={includeResolved}
              onChange={(e) => setIncludeResolved(e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-600 rounded focus:ring-blue-500 bg-gray-700"
            />
            <span className="text-sm text-gray-300">Show Resolved</span>
          </label>
        )}
      </div>

      <main className="mt-6">
        {loading && <p className="text-gray-400">Loading...</p>}
        {error && <p className="text-red-400">{error}</p>}

        {!loading && !error && activeTab === "unassigned" && (
          <div className="space-y-4">
            {unassignedAlerts.length === 0 ? (
              <p className="text-gray-400">No unassigned alerts</p>
            ) : (
              unassignedAlerts.map((alert) => (
                <div
                  key={alert.id}
                  className="bg-gray-800 p-4 rounded-md border border-gray-700 hover:border-gray-600 transition-colors"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="px-2 py-1 text-xs font-bold rounded bg-gray-700 text-gray-300">
                          #{alert.id}
                        </span>
                        <span
                          className={`px-2 py-1 text-xs font-bold rounded ${
                            alert.severity === "critical"
                              ? "bg-red-600"
                              : alert.severity === "high"
                              ? "bg-orange-600"
                              : alert.severity === "medium"
                              ? "bg-yellow-600"
                              : "bg-blue-600"
                          }`}
                        >
                          {alert.severity.toUpperCase()}
                        </span>
                        <span className="text-sm text-gray-400">
                          {alert.rule_name || alert.alert_type}
                        </span>
                      </div>
                      <p className="text-white font-medium mb-1">
                        {alert.message || JSON.stringify(alert.details)}
                      </p>
                      <div className="text-sm text-gray-400">
                        {alert.hostname && <p>Host: {alert.hostname}</p>}
                        <p>Agent ID: {alert.agent_id}</p>
                        <p>
                          Created: {new Date(alert.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    {isAdmin && (
                      <button
                        onClick={() => handleClaimAlert(alert.id)}
                        disabled={actionLoading}
                        className="ml-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:bg-gray-600"
                      >
                        Claim
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {!loading && !error && activeTab === "my-assignments" && (
          <div className="space-y-4">
            {myAssignments.length === 0 ? (
              <p className="text-gray-400">No assignments</p>
            ) : (
              myAssignments.map((assignment) => (
                <div
                  key={assignment.id}
                  className="bg-gray-800 p-4 rounded-md border border-gray-700"
                >
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <span
                        className={`px-2 py-1 text-xs font-bold rounded ${
                          assignment.status === "resolved"
                            ? "bg-green-600"
                            : assignment.status === "escalated"
                            ? "bg-purple-600"
                            : "bg-yellow-600"
                        }`}
                      >
                        {assignment.status.toUpperCase()}
                      </span>
                      {assignment.resolution && (
                        <span className="ml-2 px-2 py-1 text-xs bg-gray-700 rounded">
                          {assignment.resolution
                            .replace("_", " ")
                            .toUpperCase()}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-400">
                      Alert ID: {assignment.alert_id}
                    </p>
                  </div>
                  <p className="text-sm text-gray-300 mb-2">
                    Assigned:{" "}
                    {new Date(assignment.assigned_at).toLocaleString()}
                  </p>
                  {assignment.notes && (
                    <div className="bg-gray-900 p-3 rounded-md mb-3">
                      <p className="text-xs text-gray-400 mb-1">Notes:</p>
                      <p className="text-sm text-gray-300 whitespace-pre-wrap">
                        {assignment.notes}
                      </p>
                    </div>
                  )}
                  {isAdmin &&
                    assignment.status !== "resolved" &&
                    assignment.status !== "escalated" && (
                      <div className="flex gap-2 mt-3">
                        <button
                          onClick={() => handleOpenUpdateModal(assignment)}
                          className="px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm"
                        >
                          Update Status
                        </button>
                        <button
                          onClick={() => handleOpenEscalateModal(assignment)}
                          className="px-3 py-1 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors text-sm"
                        >
                          Escalate to Owner
                        </button>
                      </div>
                    )}
                </div>
              ))
            )}
          </div>
        )}
      </main>

      {/* Update Modal */}
      {showUpdateModal && selectedAssignment && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-lg max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">Update Assignment</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Status</label>
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-900 text-white rounded-md border border-gray-700"
                >
                  <option value="investigating">Investigating</option>
                  <option value="resolved">Resolved</option>
                </select>
              </div>
              {status === "resolved" && (
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Resolution
                  </label>
                  <select
                    value={resolution}
                    onChange={(e) => setResolution(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-900 text-white rounded-md border border-gray-700"
                  >
                    <option value="">Select resolution...</option>
                    <option value="true_positive">True Positive</option>
                    <option value="false_positive">False Positive</option>
                    <option value="benign_positive">Benign Positive</option>
                  </select>
                </div>
              )}
              <div>
                <label className="block text-sm font-medium mb-1">Notes</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={4}
                  className="w-full px-3 py-2 bg-gray-900 text-white rounded-md border border-gray-700"
                  placeholder="Add investigation notes..."
                />
              </div>
            </div>
            <div className="flex gap-2 mt-6">
              <button
                onClick={handleUpdateAssignment}
                disabled={actionLoading}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:bg-gray-600"
              >
                {actionLoading ? "Updating..." : "Update"}
              </button>
              <button
                onClick={() => setShowUpdateModal(false)}
                className="px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Escalate Modal */}
      {showEscalateModal && selectedAssignment && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-lg max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">Escalate to Owner</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Escalation Notes *
                </label>
                <textarea
                  value={escalationNotes}
                  onChange={(e) => setEscalationNotes(e.target.value)}
                  rows={4}
                  className="w-full px-3 py-2 bg-gray-900 text-white rounded-md border border-gray-700"
                  placeholder="Explain why this alert needs Owner attention..."
                  required
                />
              </div>
              <p className="text-sm text-gray-400">
                This alert will be flagged for the Owner to review. The Owner
                will receive notification.
              </p>
            </div>
            <div className="flex gap-2 mt-6">
              <button
                onClick={handleEscalateAlert}
                disabled={actionLoading || !escalationNotes.trim()}
                className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors disabled:bg-gray-600"
              >
                {actionLoading ? "Escalating..." : "Escalate"}
              </button>
              <button
                onClick={() => setShowEscalateModal(false)}
                className="px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
