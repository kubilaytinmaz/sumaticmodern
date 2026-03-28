'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { getWebSocketClient, WebSocketMessage } from '@/lib/websocket';

interface UseWebSocketReturn {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null;
  subscribe: (event: string, handler: (data: unknown) => void) => () => void;
  send: (type: string, data: unknown) => void;
  reconnect: () => void;
  disconnect: () => void;
}

export function useWebSocket(): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const clientRef = useRef<ReturnType<typeof getWebSocketClient> | null>(null);

  useEffect(() => {
    const client = getWebSocketClient();
    clientRef.current = client;

    // Connection handler
    const unsubConnection = client.on('connection', (message) => {
      setIsConnected(message.data as boolean);
    });

    // Connect with token (optional for development without auth)
    const token = localStorage.getItem('access_token');
    client.connect(token || 'development-mode');

    return () => {
      unsubConnection();
    };
  }, []);

  const subscribe = useCallback((event: string, handler: (data: unknown) => void) => {
    if (!clientRef.current) {
      return () => {};
    }

    return clientRef.current.on(event, (message) => {
      setLastMessage(message);
      handler(message.data);
    });
  }, []);

  const send = useCallback((type: string, data: unknown) => {
    if (!clientRef.current) return;

    clientRef.current.send({
      type: type as WebSocketMessage['type'],
      data,
      timestamp: new Date().toISOString(),
    });
  }, []);

  const reconnect = useCallback(() => {
    if (!clientRef.current) return;

    const token = localStorage.getItem('access_token');
    if (token) {
      clientRef.current.connect(token);
    }
  }, []);

  const disconnect = useCallback(() => {
    if (!clientRef.current) return;
    clientRef.current.disconnect();
  }, []);

  return {
    isConnected,
    lastMessage,
    subscribe,
    send,
    reconnect,
    disconnect,
  };
}

// Hook for device readings subscription
export function useDeviceReadings(deviceId?: number) {
  const [readings, setReadings] = useState<unknown[]>([]);
  const { isConnected, subscribe } = useWebSocket();

  useEffect(() => {
    const unsubscribe = subscribe('device_reading', (data) => {
      const reading = data as { device_id: number; [key: string]: unknown };
      
      // Filter by device ID if provided
      if (deviceId && reading.device_id !== deviceId) return;
      
      setReadings((prev) => {
        const newReadings = [reading, ...prev];
        // Keep only last 50 readings
        return newReadings.slice(0, 50);
      });
    });

    return unsubscribe;
  }, [subscribe, deviceId]);

  return { readings, isConnected };
}

// Hook for device status subscription
export function useDeviceStatus(deviceId?: number) {
  const [statusUpdates, setStatusUpdates] = useState<unknown[]>([]);
  const { isConnected, subscribe } = useWebSocket();

  useEffect(() => {
    const unsubscribe = subscribe('device_status', (data) => {
      const status = data as { device_id: number; [key: string]: unknown };
      
      // Filter by device ID if provided
      if (deviceId && status.device_id !== deviceId) return;
      
      setStatusUpdates((prev) => {
        const newUpdates = [status, ...prev];
        // Keep only last 20 updates
        return newUpdates.slice(0, 20);
      });
    });

    return unsubscribe;
  }, [subscribe, deviceId]);

  return { statusUpdates, isConnected };
}

// Hook for alerts subscription
export function useAlerts() {
  const [alerts, setAlerts] = useState<unknown[]>([]);
  const { isConnected, subscribe } = useWebSocket();

  useEffect(() => {
    const unsubscribe = subscribe('device_alert', (data) => {
      setAlerts((prev) => {
        const newAlerts = [data, ...prev];
        // Keep only last 50 alerts
        return newAlerts.slice(0, 50);
      });
    });

    return unsubscribe;
  }, [subscribe]);

  return { alerts, isConnected };
}
