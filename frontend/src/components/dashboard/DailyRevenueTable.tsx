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

interface ChartDataPoint {
  timestamp: string;
  label: string;
  total_value: number;
  delta: number;
  is_offline: boolean;
  offline_hours?: number;
  online_status?: string;
}

interface DailyRevenueTableProps {
  data: ChartDataPoint[];
  isLoading: boolean;
  timeRange: number;
  period?: string;
}

type SortField = 'date' | 'revenue' | 'delta' | 'offline';
type SortDirection = 'asc' | 'desc';

export default function DailyRevenueTable({ data, isLoading, timeRange, period = 'daily' }: DailyRevenueTableProps) {
  
  // Get period label for summary
  const getPeriodLabel = () => {
    switch (period) {
      case 'hourly': return 'saat';
      case 'daily': return 'gün';
      case 'weekly': return 'hafta';
      case 'monthly': return 'ay';
      default: return 'kayıt';
    }
  };
  const [sortField, setSortField] = useState<SortField>('date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  // Handle sort
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // Sort data
  const sortedData = useMemo(() => {
    if (!data || data.length === 0) return [];

    const sorted = [...data].sort((a, b) => {
      let comparison = 0;

      switch (sortField) {
        case 'date':
          comparison = a.timestamp.localeCompare(b.timestamp);
          break;
        case 'revenue':
          comparison = a.total_value - b.total_value;
          break;
        case 'delta':
          comparison = a.delta - b.delta;
          break;
        case 'offline':
          comparison = (a.offline_hours || 0) - (b.offline_hours || 0);
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
  const StatusBadge = ({ status, offlineHours }: { status?: string; offlineHours?: number }) => {
    const statusMap = {
      online: { label: 'Online', variant: 'default' as const, className: 'bg-green-500/10 text-green-600 border-green-500/20' },
      offline: { label: 'Offline', variant: 'destructive' as const, className: 'bg-red-500/10 text-red-600 border-red-500/20' },
      partial: { label: 'Kısmi', variant: 'default' as const, className: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20' },
      no_data: { label: 'Veri Yok', variant: 'secondary' as const, className: 'bg-gray-500/10 text-gray-600 border-gray-500/20' },
    };

    const statusConfig = statusMap[status as keyof typeof statusMap] || statusMap.online;

    return (
      <div className="flex items-center gap-2">
        {status === 'offline' ? (
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
  const formatOfflineHours = (hours?: number) => {
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
          <p>Seçilen zaman aralığında veri bulunamadı.</p>
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
                onClick={() => handleSort('date')}
              >
                <div className="flex items-center gap-2">
                  Tarih
                  <SortIcon field="date" />
                </div>
              </TableHead>
              <TableHead 
                className="text-right cursor-pointer select-none font-semibold"
                onClick={() => handleSort('revenue')}
              >
                <div className="flex items-center justify-end gap-2">
                  Toplam Ciro
                  <SortIcon field="revenue" />
                </div>
              </TableHead>
              <TableHead 
                className="text-right cursor-pointer select-none font-semibold"
                onClick={() => handleSort('delta')}
              >
                <div className="flex items-center justify-end gap-2">
                  Artış
                  <SortIcon field="delta" />
                </div>
              </TableHead>
              <TableHead 
                className="text-right cursor-pointer select-none font-semibold"
                onClick={() => handleSort('offline')}
              >
                <div className="flex items-center justify-end gap-2">
                  Offline Süresi
                  <SortIcon field="offline" />
                </div>
              </TableHead>
              <TableHead className="text-center font-semibold">Durum</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedData.map((row, index) => (
              <TableRow 
                key={row.timestamp}
                className={index % 2 === 0 ? 'bg-background' : 'bg-muted/20'}
              >
                <TableCell className="font-medium">
                  <div>
                    <div className="font-semibold">{row.label}</div>
                  </div>
                </TableCell>
                <TableCell className="text-right font-mono text-base">
                  {formatMoney(row.total_value)}
                </TableCell>
                <TableCell className="text-right">
                  <span
                    className={`font-mono font-semibold ${
                      row.delta > 0
                        ? 'text-green-600'
                        : row.delta === 0
                        ? 'text-muted-foreground'
                        : 'text-red-600'
                    }`}
                  >
                    {row.delta > 0 ? '+' : ''}
                    {formatMoney(row.delta)}
                  </span>
                </TableCell>
                <TableCell className="text-right">
                  <span
                    className={`text-sm ${
                      (row.offline_hours || 0) > 0 ? 'text-orange-600 font-medium' : 'text-muted-foreground'
                    }`}
                  >
                    {formatOfflineHours(row.offline_hours)}
                  </span>
                </TableCell>
                <TableCell className="text-center">
                  <StatusBadge status={row.online_status} offlineHours={row.offline_hours} />
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
            Toplam {sortedData.length} {getPeriodLabel()}
          </span>
          <div className="flex gap-6">
            <div>
              <span className="text-muted-foreground">Toplam Artış: </span>
              <span className="font-semibold text-green-600">
                +{formatMoney(sortedData.reduce((sum, row) => sum + row.delta, 0))}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Toplam Offline: </span>
              <span className="font-semibold text-orange-600">
                {formatOfflineHours(sortedData.reduce((sum, row) => sum + (row.offline_hours || 0), 0))}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
