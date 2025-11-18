// src/hooks/useWebSocket.ts
import { useEffect, useRef } from "react";
import { useAuth } from "../contexts/AuthContext";

const WEBSOCKET_URL = "ws://127.0.0.1:8000/ws";

export function useWebSocket(onMessage: (data: any) => void) {
  const { token } = useAuth();
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!token) return; // Don't connect if not logged in

    // Create a new WebSocket connection
    const socket = new WebSocket(WEBSOCKET_URL);
    ws.current = socket;

    socket.onopen = () => {
      console.log("WebSocket connected");
      // Send the auth token as the first message
      socket.send(JSON.stringify({ token }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("WebSocket message received:", data);
      onMessage(data); // Pass the message to the component
    };

    socket.onclose = () => {
      console.log("WebSocket disconnected");
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    // Cleanup function: close the socket when the component unmounts
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [token, onMessage]); // Re-run if the token or callback changes
}
