import { REFRESH_INTERVALS, WS_STATE } from './constants';

// In production: NEXT_PUBLIC_WS_URL should be set (e.g., wss://sumatic.com)
// In development: fallback to ws://localhost:8000
// The key fix: do NOT include port from window.location in production
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

/**
 * WebSocket message type definition
 */
export interface WebSocketMessage {
  type: 'connection' | 'device_reading' | 'device_status' | 'status_change' | 'device_alert' | 'ping' | 'pong';
  data: unknown;
  timestamp: string;
}

/**
 * WebSocket event callback type
 */
type WebSocketCallback = (message: WebSocketMessage) => void;

/**
 * WebSocket client class
 * Singleton pattern for global WebSocket connection management
 */
class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private token: string | null = null;
  private listeners: Map<string, Set<WebSocketCallback>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private pingInterval: NodeJS.Timeout | null = null;
  private isIntentionallyClosed = false;

  constructor(url: string) {
    this.url = url;
  }

  /**
   * Connect to WebSocket server
   */
  connect(token?: string): void {
    // Only run in browser environment
    if (typeof window === 'undefined') return;

    if (token) {
      this.token = token;
    }

    this.isIntentionallyClosed = false;

    // Close existing connection if any
    if (this.ws && this.ws.readyState === WS_STATE.OPEN) {
      return;
    }

    try {
      // Build WebSocket URL with token (must include /api/v1 prefix)
      const wsUrl = this.token
        ? `${this.url}/api/v1/ws?token=${this.token}`
        : `${this.url}/api/v1/ws`;

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected');
        this.reconnectAttempts = 0;
        this.emit({
          type: 'connection',
          data: true,
          timestamp: new Date().toISOString(),
        });

        // Start ping interval to keep connection alive
        this.startPingInterval();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.emit(message);
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        this.emit({
          type: 'connection',
          data: false,
          timestamp: new Date().toISOString(),
        });
      };

      this.ws.onclose = () => {
        console.log('[WebSocket] Disconnected');
        this.stopPingInterval();
        this.emit({
          type: 'connection',
          data: false,
          timestamp: new Date().toISOString(),
        });

        // Attempt to reconnect if not intentionally closed
        if (!this.isIntentionallyClosed) {
          this.scheduleReconnect();
        }
      };
    } catch (error) {
      console.error('[WebSocket] Connection failed:', error);
      this.scheduleReconnect();
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.isIntentionallyClosed = true;
    this.stopPingInterval();
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Schedule reconnection attempt
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnect attempts reached');
      return;
    }

    if (this.reconnectTimeout) {
      return; // Already scheduled
    }

    const delay = Math.min(
      REFRESH_INTERVALS.WEBSOCKET * Math.pow(2, this.reconnectAttempts),
      30000 // Max 30 seconds
    );

    console.log(`[WebSocket] Reconnecting in ${delay / 1000}s (attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`);

    this.reconnectTimeout = setTimeout(() => {
      this.reconnectTimeout = null;
      this.reconnectAttempts++;
      this.connect();
    }, delay);
  }

  /**
   * Start ping interval to keep connection alive
   */
  private startPingInterval(): void {
    this.stopPingInterval();
    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WS_STATE.OPEN) {
        this.send({
          type: 'ping',
          data: null,
          timestamp: new Date().toISOString(),
        });
      }
    }, 30000); // Ping every 30 seconds
  }

  /**
   * Stop ping interval
   */
  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Send a message through WebSocket
   */
  send(message: WebSocketMessage): void {
    if (this.ws && this.ws.readyState === WS_STATE.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('[WebSocket] Cannot send message - not connected');
    }
  }

  /**
   * Subscribe to WebSocket events
   */
  on(event: string, callback: WebSocketCallback): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);

    // Return unsubscribe function
    return () => {
      const callbacks = this.listeners.get(event);
      if (callbacks) {
        callbacks.delete(callback);
        if (callbacks.size === 0) {
          this.listeners.delete(event);
        }
      }
    };
  }

  /**
   * Emit event to all subscribers
   */
  private emit(message: WebSocketMessage): void {
    const callbacks = this.listeners.get(message.type);
    if (callbacks) {
      callbacks.forEach((callback) => {
        try {
          callback(message);
        } catch (error) {
          console.error(`[WebSocket] Error in ${message.type} callback:`, error);
        }
      });
    }

    // Also emit to wildcard listeners
    const wildcardCallbacks = this.listeners.get('*');
    if (wildcardCallbacks) {
      wildcardCallbacks.forEach((callback) => {
        try {
          callback(message);
        } catch (error) {
          console.error('[WebSocket] Error in wildcard callback:', error);
        }
      });
    }
  }

  /**
   * Get connection state
   */
  get readyState(): number {
    return this.ws?.readyState ?? WS_STATE.CLOSED;
  }

  /**
   * Check if connected
   */
  get isConnected(): boolean {
    return this.ws?.readyState === WS_STATE.OPEN;
  }
}

// Singleton instance
let wsClient: WebSocketClient | null = null;

/**
 * Get or create WebSocket client singleton
 */
export function getWebSocketClient(): WebSocketClient {
  if (!wsClient) {
    wsClient = new WebSocketClient(WS_BASE_URL);
  }
  return wsClient;
}
