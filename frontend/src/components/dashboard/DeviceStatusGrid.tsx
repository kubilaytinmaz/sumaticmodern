'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Device } from '@/types/device';
import { cn } from '@/lib/utils';

interface DeviceStatusGridProps {
  devices: Device[];
  isLoading?: boolean;
  onDeviceClick?: (device: Device) => void;
}

export function DeviceStatusGrid({ devices, isLoading = false, onDeviceClick }: DeviceStatusGridProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Cihaz Durumları</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10 gap-2">
            {Array.from({ length: 20 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const getStatusColor = (device: Device) => {
    // Use status field if available, otherwise fall back to is_online boolean
    if (device.status) {
      switch (device.status) {
        case 'ONLINE':
          return 'bg-green-500 hover:bg-green-600';
        case 'OFFLINE':
          return 'bg-red-500 hover:bg-red-600';
        case 'PENDING':
          return 'bg-yellow-500 hover:bg-yellow-600';
        default:
          return 'bg-gray-500 hover:bg-gray-600';
      }
    }
    
    // Fallback to is_online boolean
    if (device.is_online === true) {
      return 'bg-green-500 hover:bg-green-600';
    } else if (device.is_online === false) {
      return 'bg-red-500 hover:bg-red-600';
    }
    return 'bg-gray-500 hover:bg-gray-600';
  };

  const getStatusLabel = (device: Device) => {
    if (device.status) {
      switch (device.status) {
        case 'ONLINE':
          return 'Online';
        case 'OFFLINE':
          return 'Offline';
        case 'PENDING':
          return 'Beklemede';
        default:
          return 'Bilinmiyor';
      }
    }
    
    // Fallback to is_online boolean
    if (device.is_online === true) return 'Online';
    if (device.is_online === false) return 'Offline';
    return 'Bilinmiyor';
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Cihaz Durumları</CardTitle>
          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-full bg-green-500" />
              <span className="text-muted-foreground">Online</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-full bg-red-500" />
              <span className="text-muted-foreground">Offline</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-full bg-yellow-500" />
              <span className="text-muted-foreground">Beklemede</span>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10 gap-2">
          {devices.map((device) => (
            <button
              key={device.id}
              onClick={() => onDeviceClick?.(device)}
              className={cn(
                'flex items-center justify-center rounded px-2 py-1.5 text-xs font-medium text-white transition-colors',
                getStatusColor(device)
              )}
              title={`${device.name} (${device.device_code}) - ${getStatusLabel(device)}`}
            >
              {device.device_code}
            </button>
          ))}
        </div>
        {devices.length === 0 && (
          <p className="text-center text-sm text-muted-foreground py-4">
            Henüz cihaz bulunmuyor
          </p>
        )}
      </CardContent>
    </Card>
  );
}
