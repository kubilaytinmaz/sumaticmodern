'use client';

import { cn } from '@/lib/utils';
import { Wifi, WifiOff, Loader2 } from 'lucide-react';

interface RealtimeIndicatorProps {
  isConnected: boolean;
  isConnecting?: boolean;
  className?: string;
}

export function RealtimeIndicator({
  isConnected,
  isConnecting = false,
  className,
}: RealtimeIndicatorProps) {
  return (
    <div
      className={cn(
        'flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
        isConnected
          ? 'bg-green-500/10 text-green-500'
          : isConnecting
          ? 'bg-yellow-500/10 text-yellow-500'
          : 'bg-red-500/10 text-red-500',
        className
      )}
    >
      {isConnecting ? (
        <>
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          <span>Bağlanıyor...</span>
        </>
      ) : isConnected ? (
        <>
          <Wifi className="h-3.5 w-3.5" />
          <span>Canlı</span>
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
          </span>
        </>
      ) : (
        <>
          <WifiOff className="h-3.5 w-3.5" />
          <span>Bağlantı Kesildi</span>
        </>
      )}
    </div>
  );
}
