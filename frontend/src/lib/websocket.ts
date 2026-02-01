/**
 * WebSocket client with auto-reconnection for CICD Monitor.
 */

import type { WebSocketMessage } from "./types";

export type MessageHandler = (message: WebSocketMessage) => void;
export type ConnectionHandler = (connected: boolean) => void;

const WS_URL = "ws://localhost:8000/ws";
const RECONNECT_DELAY = 3000;

export class MonitorWebSocket {
  private ws: WebSocket | null = null;
  private messageHandlers: MessageHandler[] = [];
  private connectionHandlers: ConnectionHandler[] = [];
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private isManualClose = false;

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.isManualClose = false;
    this.ws = new WebSocket(WS_URL);

    this.ws.onopen = () => {
      console.log("[WS] Connected to monitor server");
      this.notifyConnection(true);
    };

    this.ws.onclose = () => {
      console.log("[WS] Disconnected from monitor server");
      this.notifyConnection(false);

      // Auto-reconnect unless manually closed
      if (!this.isManualClose) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error("[WS] Error:", error);
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        this.notifyMessage(message);
      } catch (e) {
        console.error("[WS] Failed to parse message:", e);
      }
    };
  }

  disconnect(): void {
    this.isManualClose = true;
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }
    this.reconnectTimeout = setTimeout(() => {
      console.log("[WS] Attempting to reconnect...");
      this.connect();
    }, RECONNECT_DELAY);
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.push(handler);
    return () => {
      const index = this.messageHandlers.indexOf(handler);
      if (index > -1) {
        this.messageHandlers.splice(index, 1);
      }
    };
  }

  onConnection(handler: ConnectionHandler): () => void {
    this.connectionHandlers.push(handler);
    return () => {
      const index = this.connectionHandlers.indexOf(handler);
      if (index > -1) {
        this.connectionHandlers.splice(index, 1);
      }
    };
  }

  private notifyMessage(message: WebSocketMessage): void {
    for (const handler of this.messageHandlers) {
      handler(message);
    }
  }

  private notifyConnection(connected: boolean): void {
    for (const handler of this.connectionHandlers) {
      handler(connected);
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// Singleton instance
export const monitorWS = new MonitorWebSocket();
