// src/components/InviteTokenModal.tsx
import { useState } from "react";

interface InviteTokenModalProps {
  isOpen: boolean;
  onClose: () => void;
  token: string | null;
  expiresAt: string | null;
}

export default function InviteTokenModal({
  isOpen,
  onClose,
  token,
  expiresAt,
}: InviteTokenModalProps) {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleCopy = async (): Promise<void> => {
    if (token) {
      await navigator.clipboard.writeText(token);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatExpiryTime = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

    if (diffHours > 24) {
      const days = Math.floor(diffHours / 24);
      return `${days} day${days > 1 ? "s" : ""}`;
    } else if (diffHours > 0) {
      return `${diffHours} hour${diffHours > 1 ? "s" : ""} ${diffMinutes} min`;
    } else {
      return `${diffMinutes} minute${diffMinutes > 1 ? "s" : ""}`;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-2xl mx-4">
        {/* Header */}
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-white">
            Device Invitation Token
          </h2>
          <button
            onClick={onClose}
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

        {/* Token Display */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Token (use this to register your device)
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={token || ""}
              readOnly
              className="flex-1 px-4 py-2 bg-gray-900 text-green-400 font-mono text-sm rounded border border-gray-700 focus:outline-none focus:border-blue-500"
            />
            <button
              onClick={handleCopy}
              className={`px-4 py-2 rounded font-medium transition-colors ${
                copied
                  ? "bg-green-600 text-white"
                  : "bg-blue-600 text-white hover:bg-blue-700"
              }`}
            >
              {copied ? (
                <span className="flex items-center gap-2">
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  Copied!
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                    />
                  </svg>
                  Copy
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Expiry Info */}
        {expiresAt && (
          <div className="mb-6 p-4 bg-yellow-900 bg-opacity-30 border border-yellow-700 rounded">
            <div className="flex items-start gap-2">
              <svg
                className="w-5 h-5 text-yellow-500 mt-0.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div>
                <p className="text-sm font-medium text-yellow-300">
                  Token expires in {formatExpiryTime(expiresAt)}
                </p>
                <p className="text-xs text-yellow-400 mt-1">
                  {new Date(expiresAt).toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Usage Instructions */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-3">
            How to Use This Token
          </h3>
          <ol className="space-y-2 text-sm text-gray-300">
            <li className="flex gap-2">
              <span className="font-bold text-blue-400">1.</span>
              <span>Copy the token above using the Copy button</span>
            </li>
            <li className="flex gap-2">
              <span className="font-bold text-blue-400">2.</span>
              <span>
                On your target device, install the Aegis agent if not already
                installed
              </span>
            </li>
            <li className="flex gap-2">
              <span className="font-bold text-blue-400">3.</span>
              <span>
                Run the registration command:
                <code className="ml-2 px-2 py-1 bg-gray-900 text-green-400 rounded font-mono text-xs">
                  sudo python main.py register --token YOUR_TOKEN
                </code>
              </span>
            </li>
            <li className="flex gap-2">
              <span className="font-bold text-blue-400">4.</span>
              <span>
                The device will appear in your dashboard once registered
              </span>
            </li>
          </ol>
        </div>

        {/* Security Note */}
        <div className="mb-6 p-4 bg-red-900 bg-opacity-20 border border-red-700 rounded">
          <div className="flex items-start gap-2">
            <svg
              className="w-5 h-5 text-red-500 mt-0.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <div>
              <p className="text-sm font-medium text-red-300">
                Security Notice
              </p>
              <p className="text-xs text-red-400 mt-1">
                Keep this token secure. Anyone with this token can register a
                device to your account. The token is single-use and will expire
                after use or after the time limit.
              </p>
            </div>
          </div>
        </div>

        {/* Close Button */}
        <div className="flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-gray-700 text-white rounded hover:bg-gray-600 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
