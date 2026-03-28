'use client';

import { useState, useMemo } from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown, Wifi, WifiOff } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { formatMoney, formatDate } from '@/lib/utils';

export interface DeviceTableRow {
  id: number;
  device_code: string;
  device_name: string;
  modem_id: string;
  device_addr: number;
  current_value: number;
  last_delta: number;
  total_delta: number;
  avg_delta: number;
  offline_hours: number;
  online_status: string;
  is_online: boolean;
  last_reading_at: string | null;
}

interface DeviceRevenueTableProps {
  data: DeviceTableRow[];
  isLoading: boolean;
  period: string;
  onDeviceClick?: (deviceId: number) => void;
}

type SortField = 'code' | 'name' | 'current_value' | 'last_delta' | 'offline_hours' | 'status';
type SortDirection = 'asc' | 'desc';

export default function DeviceRevenueTable({ data, isLoading, period, onDeviceClick }: DeviceRevenueTableProps) {
  const [sortField, setSortField] = useState<SortField>('code');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  // Handle sort
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Sort data
  const sortedData = useMemo(() => {
    if (!data || data.length === 0) return [];

    const sorted = [...data].sort((a, b) => {
      let comparison = 0;

      switch (sortField) {
        case 'code':
          comparison = a.device_code.localeCompare(b.device_code);
          break;
        case 'name':
          comparison = a.device_name.localeCompare(b.device_name);
          break;
        case 'current_value':
          comparison = a.current_value - b.current_value;
          break;
        case 'last_delta':
          comparison = a.last_delta - b.last_delta;
          break;
        case 'offline_hours':
          comparison = a.offline_hours - b.offline_hours;
          break;
        case 'status':
          comparison = a.is_online === b.is_online ? 0 : a.is_online ? 1 : -1;
          break;
      }

      return sortDirection === 'asc' ? comparison : -comparison;
    });

    return sorted;
  }, [data, sortField, sortDirection]);

  // Helper function for sort icon
  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <ArrowUpDown className="h-4 w-4 text-muted-foreground" />;
    }
    return sortDirection === 'asc' ? (
      <ArrowUp className="h-4 w-4" />
    ) : (
      <ArrowDown className="h-4 w-4" />
    );
  };

  // Helper function for status badge
  const StatusBadge = ({ status, isOnline }: { status: string; isOnline: boolean }) => {
    const statusMap: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive'; className: string }> = {
      online: { label: 'Çevrimiçi', variant: 'default', className: 'bg-green-500/10 text-green-600 border-green-500/20' },
      offline: { label: 'Çevrimdışı', variant: 'destructive', className: 'bg-red-500/10 text-red-600 border-red-500/20' },
      partial: { label: 'Kısmi', variant: 'default', className: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20' },
      no_data: { label: 'Veri Yok', variant: 'secondary', className: 'bg-gray-500/10 text-gray-600 border-gray-500/20' },
      error: { label: 'Hata', variant: 'destructive', className: 'bg-red-500/10 text-red-600 border-red-500/20' },
    };

    const statusConfig = statusMap[status] || statusMap.no_data;

    return (
      <div className="flex items-center gap-2">
        {status === 'offline' || status === 'error' ? (
          <WifiOff className="h-4 w-4 text-red-500" />
        ) : (
          <Wifi className={`h-4 w-4 ${status === 'partial' ? 'text-yellow-500' : 'text-green-500'}`} />
        )}
        <Badge variant={statusConfig.variant} className={`${statusConfig.className} border`}>
          {statusConfig.label}
        </Badge>
      </div>
    );
  };

  // Helper function for offline hours formatting
  const formatOfflineHours = (hours: number) => {
    if (!hours || hours === 0) return '0 saat';
    if (hours < 1) return `${Math.round(hours * 60)} dk`;
    if (hours >= 24) {
      const days = Math.floor(hours / 24);
      const remainingHours = Math.round(hours % 24);
      return remainingHours > 0 ? `${days} gün ${remainingHours} saat` : `${days} gün`;
    }
    return `${hours.toFixed(1)} saat`;
  };

  if (isLoading) {
    return (
      <div className="rounded-md border">
        <div className="p-8 text-center text-muted-foreground">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]"></div>
          <p className="mt-4">Veriler yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="rounded-md border">
        <div className="p-8 text-center text-muted-foreground">
          <p>Cihaz verisi bulunamadı.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-md border bg-card">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50 hover:bg-muted/50">
              <TableHead 
                className="cursor-pointer select-none font-semibold"
                onClick={() => handleSort('code')}
              >
                <div className="flex items-center gap-2">
                  Cihaz Kodu
                  <SortIcon field="code" />
                </div>
              </TableHead>
              <TableHead 
                className="cursor-pointer select-none font-semibold"
                onClick={() => handleSort('name')}
              >
                <div className="flex items-center gap-2">
                  İsim
                  <SortIcon field="name" />
                </div>
              </TableHead>
              <TableHead 
                className="text-right cursor-pointer select-none font-semibold"
                onClick={() => handleSort('current_value')}
              >
                <div className="flex items-center justify-end gap-2">
                  Güncel Değer
                  <SortIcon field="current_value" />
                </div>
              </TableHead>
              <TableHead 
                className="text-right cursor-pointer select-none font-semibold"
                onClick={() => handleSort('last_delta')}
              >
                <div className="flex items-center justify-end gap-2">
                  Son Artış
                  <SortIcon field="last_delta" />
                </div>
              </TableHead>
              <TableHead 
                className="text-right cursor-pointer select-none font-semibold"
                onClick={() => handleSort('offline_hours')}
              >
                <div className="flex items-center justify-end gap-2">
                  Offline Süresi
                  <SortIcon field="offline_hours" />
                </div>
              </TableHead>
              <TableHead 
                className="text-center cursor-pointer select-none font-semibold"
                onClick={() => handleSort('status')}
              >
                <div className="flex items-center justify-center gap-2">
                  Durum
                  <SortIcon field="status" />
                </div>
              </TableHead>
              <TableHead className="text-left font-semibold">Son Veri</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedData.map((row, index) => (
              <TableRow 
                key={row.id}
                className={`${index % 2 === 0 ? 'bg-background' : 'bg-muted/20'} ${onDeviceClick ? 'hover:bg-muted/50 cursor-pointer transition-colors' : ''}`}
                onClick={() => onDeviceClick?.(row.id)}
              >
                <TableCell className="font-bold">{row.device_code}</TableCell>
                <TableCell className="font-medium">{row.device_name}</TableCell>
                <TableCell className="text-right font-mono text-base">
                  {formatMoney(row.current_value)}
                </TableCell>
                <TableCell className="text-right">
                  <span
                    className={`font-mono font-semibold ${
                      row.last_delta > 0
                        ? 'text-green-600'
                        : row.last_delta === 0
                        ? 'text-muted-foreground'
                        : 'text-red-600'
                    }`}
                  >
                    {row.last_delta > 0 ? '+' : ''}
                    {formatMoney(row.last_delta, false)} ₺
                  </span>
                </TableCell>
                <TableCell className="text-right">
                  <span
                    className={`text-sm ${
                      row.offline_hours > 0 ? 'text-orange-600 font-medium' : 'text-muted-foreground'
                    }`}
                  >
                    {formatOfflineHours(row.offline_hours)}
                  </span>
                </TableCell>
                <TableCell className="text-center">
                  <StatusBadge status={row.online_status} isOnline={row.is_online} />
                </TableCell>
                <TableCell className="text-left text-xs text-muted-foreground">
                  {row.last_reading_at ? formatDate(row.last_reading_at) : '-'}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Summary Footer */}
      <div className="border-t bg-muted/30 px-6 py-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            Toplam {sortedData.length} cihaz
          </span>
          <div className="flex gap-6">
            <div>
              <span className="text-muted-foreground">Toplam Değer: </span>
              <span className="font-semibold text-blue-600">
                {formatMoney(sortedData.reduce((sum, row) => sum + row.current_value, 0))}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Toplam Artış: </span>
              <span className="font-semibold text-green-600">
                +{formatMoney(sortedData.reduce((sum, row) => sum + row.last_delta, 0))}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Toplam Offline: </span>
              <span className="font-semibold text-orange-600">
                {formatOfflineHours(sortedData.reduce((sum, row) => sum + row.offline_hours, 0))}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
