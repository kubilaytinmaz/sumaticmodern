'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Device, DeviceCreate, DeviceUpdate, DeviceSummary } from '@/types/device';
import { api, endpoints } from '@/lib/api';
import { useAuth } from './useAuth';
import { getWebSocketClient } from '@/lib/websocket';

interface DevicesState {
  devices: Device[];
  deviceSummaries: DeviceSummary[];
  selectedDevice: Device | null;
  isLoading: boolean;
  error: string | null;
}

interface UseDevicesReturn extends DevicesState {
  fetchDevices: () => Promise<void>;
  fetchDevice: (id: number) => Promise<Device | null>;
  createDevice: (data: DeviceCreate) => Promise<Device>;
  updateDevice: (id: number, data: DeviceUpdate) => Promise<Device>;
  deleteDevice: (id: number) => Promise<void>;
  selectDevice: (device: Device | null) => void;
  refreshDevices: () => Promise<void>;
}

export function useDevices(): UseDevicesReturn {
  const { isAuthenticated } = useAuth();
  
  const [state, setState] = useState<DevicesState>({
    devices: [],
    deviceSummaries: [],
    selectedDevice: null,
    isLoading: false,
    error: null,
  });

  const fetchDevices = useCallback(async () => {
    if (!isAuthenticated) return;
    
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    
    try {
      const devices = await api.get<Device[]>(endpoints.devices);
      setState((prev) => ({
        ...prev,
        devices,
        isLoading: false,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Cihazlar yüklenemedi';
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
    }
  }, [isAuthenticated]);

  const fetchDevice = useCallback(async (id: number): Promise<Device | null> => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    
    try {
      const device = await api.get<Device>(endpoints.device(id));
      setState((prev) => ({
        ...prev,
        selectedDevice: device,
        isLoading: false,
      }));
      return device;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Cihaz yüklenemedi';
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
      return null;
    }
  }, []);

  const createDevice = useCallback(async (data: DeviceCreate): Promise<Device> => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    
    try {
      const device = await api.post<Device>(endpoints.devices, data);
      setState((prev) => ({
        ...prev,
        devices: [...prev.devices, device],
        isLoading: false,
      }));
      return device;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Cihaz oluşturulamadı';
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
      throw error;
    }
  }, []);

  const updateDevice = useCallback(async (id: number, data: DeviceUpdate): Promise<Device> => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    
    try {
      const device = await api.put<Device>(endpoints.device(id), data);
      setState((prev) => ({
        ...prev,
        devices: prev.devices.map((d) => (d.id === id ? device : d)),
        selectedDevice: prev.selectedDevice?.id === id ? device : prev.selectedDevice,
        isLoading: false,
      }));
      return device;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Cihaz güncellenemedi';
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
      throw error;
    }
  }, []);

  const deleteDevice = useCallback(async (id: number): Promise<void> => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    
    try {
      await api.delete(endpoints.device(id));
      setState((prev) => ({
        ...prev,
        devices: prev.devices.filter((d) => d.id !== id),
        selectedDevice: prev.selectedDevice?.id === id ? null : prev.selectedDevice,
        isLoading: false,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Cihaz silinemedi';
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
      throw error;
    }
  }, []);

  const selectDevice = useCallback((device: Device | null) => {
    setState((prev) => ({ ...prev, selectedDevice: device }));
  }, []);

  const refreshDevices = useCallback(async () => {
    await fetchDevices();
  }, [fetchDevices]);

  // Fetch devices on mount if authenticated
  useEffect(() => {
    if (isAuthenticated) {
      fetchDevices();
    }
  }, [isAuthenticated, fetchDevices]);

  // Listen for WebSocket status_change events to update device status in real-time
  useEffect(() => {
    const client = getWebSocketClient();

    const unsubStatusChange = client.on('status_change', (message) => {
      const data = message.data as { device_id?: number; status?: string };
      if (data?.device_id && data?.status) {
        setState((prev) => ({
          ...prev,
          devices: prev.devices.map((d) => {
            if (d.id === data.device_id) {
              return {
                ...d,
                status: data.status as 'ONLINE' | 'OFFLINE' | 'PENDING',
                is_online: data.status === 'ONLINE',
              } as Device;
            }
            return d;
          }),
          selectedDevice:
            prev.selectedDevice?.id === data.device_id
              ? ({
                  ...prev.selectedDevice,
                  status: data.status as 'ONLINE' | 'OFFLINE' | 'PENDING',
                  is_online: data.status === 'ONLINE',
                } as Device)
              : prev.selectedDevice,
        }));
      }
    });

    return () => {
      unsubStatusChange();
    };
  }, []);

  return {
    ...state,
    fetchDevices,
    fetchDevice,
    createDevice,
    updateDevice,
    deleteDevice,
    selectDevice,
    refreshDevices,
  };
}

// Hook for single device
export function useDevice(id: number) {
  const [device, setDevice] = useState<Device | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDevice = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        const data = await api.get<Device>(endpoints.device(id));
        setDevice(data);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Cihaz yüklenemedi';
        setError(message);
      } finally {
        setIsLoading(false);
      }
    };

    if (id) {
      fetchDevice();
    }
  }, [id]);

  return { device, isLoading, error };
}
