'use client';

import { useMemo, useEffect, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export interface HourlyStatusData {
  device_id: number;
  device_code: string;
  hour_start: string;
  status: 'ONLINE' | 'OFFLINE' | 'PARTIAL';
  online_minutes: number;
  offline_minutes: number;
  data_points: number;
}

interface HourlyStatusChartProps {
  year: number;
  month: number;
  title?: string;
}

interface ChartDataPoint {
  time: string;
  ONLINE: number;
  OFFLINE: number;
  PARTIAL: number;
  [key: string]: string | number;
}

const STATUS_COLORS = {
  ONLINE: '#10b981',    // green
  OFFLINE: '#ef4444',   // red
  PARTIAL: '#f59e0b',   // amber
};

const STATUS_LABELS = {
  ONLINE: 'Çevrimiçi',
  OFFLINE: 'Çevrimdışı',
  PARTIAL: 'Kısmi',
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function HourlyStatusChart({ year, month, title }: HourlyStatusChartProps) {
  const [data, setData] = useState<HourlyStatusData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const startDate = `${year}-${String(month).padStart(2, '0')}-01`;
        const endDate = new Date(year, month, 0).toISOString().split('T')[0];
        
        const response = await fetch(
          `${API_BASE_URL}/api/v1/charts/devices/hourly-status?start_date=${startDate}&end_date=${endDate}`
        );
        
        if (!response.ok) {
          throw new Error('Veri alınamadı');
        }
        
        const result = await response.json();
        setData(result.data || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Bir hata oluştu');
        setData([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [year, month]);

  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];

    const timeMap = new Map<string, ChartDataPoint>();

    data.forEach((item: HourlyStatusData) => {
      const hourKey = new Date(item.hour_start).toISOString();
      
      if (!timeMap.has(hourKey)) {
        timeMap.set(hourKey, {
          time: new Date(item.hour_start).toLocaleString('tr-TR', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
          }),
          ONLINE: 0,
          OFFLINE: 0,
          PARTIAL: 0,
        });
      }
      
      const point = timeMap.get(hourKey)!;
      point[item.status]++;
    });

    return Array.from(timeMap.values()).sort((a, b) => 
      new Date(a.time).getTime() - new Date(b.time).getTime()
    );
  }, [data]);

  const summaryStats = useMemo(() => {
    if (!data || data.length === 0) {
      return { ONLINE: 0, OFFLINE: 0, PARTIAL: 0, total: 0 };
    }

    const timestamps = data.map((d: HourlyStatusData) => new Date(d.hour_start).getTime());
    const latestHour = Math.max(...timestamps);
    
    const latestData = data
      .filter((d: HourlyStatusData) => new Date(d.hour_start).getTime() === latestHour);

    return {
      ONLINE: latestData.filter((d: HourlyStatusData) => d.status === 'ONLINE').length,
      OFFLINE: latestData.filter((d: HourlyStatusData) => d.status === 'OFFLINE').length,
      PARTIAL: latestData.filter((d: HourlyStatusData) => d.status === 'PARTIAL').length,
      total: latestData.length,
    };
  }, [data]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className="text-lg">📊</span>
            {title || 'Saatlik Durum Analizi'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className="text-lg">📊</span>
            {title || 'Saatlik Durum Analizi'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <p className="text-muted-foreground">
              {error || 'Bu dönem için saatlik durum verisi bulunmuyor.'}
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              Veriler MQTT consumer tarafından her saat başı otomatik olarak kaydedilir.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="text-lg">📊</span>
          {title || 'Saatlik Durum Analizi'}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Summary Stats */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-green-50 dark:bg-green-950 p-4 rounded-lg">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {summaryStats.ONLINE}
            </div>
            <div className="text-sm text-green-700 dark:text-green-300">
              Çevrimiçi
            </div>
          </div>
          <div className="bg-red-50 dark:bg-red-950 p-4 rounded-lg">
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">
              {summaryStats.OFFLINE}
            </div>
            <div className="text-sm text-red-700 dark:text-red-300">
              Çevrimdışı
            </div>
          </div>
          <div className="bg-amber-50 dark:bg-amber-950 p-4 rounded-lg">
            <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">
              {summaryStats.PARTIAL}
            </div>
            <div className="text-sm text-amber-700 dark:text-amber-300">
              Kısmi
            </div>
          </div>
          <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
            <div className="text-2xl font-bold text-gray-600 dark:text-gray-400">
              {summaryStats.total}
            </div>
            <div className="text-sm text-gray-700 dark:text-gray-300">
              Toplam Cihaz
            </div>
          </div>
        </div>

        {/* Chart */}
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="time" 
                tick={{ fontSize: 12 }}
                angle={-45}
                textAnchor="end"
                height={60}
              />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="ONLINE" stackId="status" fill={STATUS_COLORS.ONLINE} name={STATUS_LABELS.ONLINE}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={STATUS_COLORS.ONLINE} />
                ))}
              </Bar>
              <Bar dataKey="OFFLINE" stackId="status" fill={STATUS_COLORS.OFFLINE} name={STATUS_LABELS.OFFLINE}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={STATUS_COLORS.OFFLINE} />
                ))}
              </Bar>
              <Bar dataKey="PARTIAL" stackId="status" fill={STATUS_COLORS.PARTIAL} name={STATUS_LABELS.PARTIAL}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={STATUS_COLORS.PARTIAL} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Info */}
        <div className="mt-4 text-sm text-muted-foreground">
          <p>
            <strong>Durum Kriterleri:</strong> Çevrimiçi (≥55 dk), Çevrimdışı (≥55 dk), Kısmi (arasında)
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
