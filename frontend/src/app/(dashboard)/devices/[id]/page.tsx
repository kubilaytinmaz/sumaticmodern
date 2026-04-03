'use client';

import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Wifi, WifiOff, MapPin, Monitor, LineChart as LineChartIcon, BarChart3 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChartMetricsHeader } from '@/components/dashboard';
import DailyRevenueTable from '@/components/dashboard/DailyRevenueTable';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
  ComposedChart,
  LabelList,
  Legend,
} from 'recharts';
import { CHART_COLORS } from '@/lib/constants';
import { formatMoney, formatDate } from '@/lib/utils';
import { useEffect, useState, useCallback } from 'react';

interface ChartDataPoint {
  timestamp: string;
  label: string;
  total_value: number;
  delta: number;
  delta_19l?: number;
  delta_5l?: number;
  total_value_19l?: number;
  total_value_5l?: number;
  is_offline: boolean;
  offline_hours?: number;
  online_status?: string;
}

interface ChartResponse {
  device_id: number;
  device_name: string;
  period: string;
  slots: number;
  data: ChartDataPoint[];
  summary: {
    current_value: number;
    min_delta: number;
    max_delta: number;
    avg_delta: number;
    total_delta: number;
  };
  monthly_revenue?: number;
  monthly_revenue_19l?: number;
  monthly_revenue_5l?: number;
}

interface DeviceInfo {
  id: number;
  device_code: string;
  name: string;
  modem_id: string;
  device_addr: number;
  last_reading_at: string | null;
  counter_19l: number;
  counter_5l: number;
  total: number;
  fault_status: number;
  is_online: boolean;
}

// Süre seçenekleri (Mum sayısı)
const SLOT_OPTIONS = [
  { value: '7', label: '1 Hafta', slots: 7 },
  { value: '14', label: '2 Hafta', slots: 14 },
  { value: '30', label: '1 Ay', slots: 30 },
] as const;

// Periyot seçenekleri
const PERIOD_OPTIONS = [
  { value: '10min', label: '10 Dakikalık' },
  { value: 'hourly', label: 'Saatlik' },
  { value: 'daily', label: 'Günlük' },
  { value: 'weekly', label: 'Haftalık' },
  { value: 'monthly', label: 'Aylık' },
];

// Metrik seçenekleri
const METRIC_OPTIONS = [
  { value: 'sayac1', label: 'Sayaç 1 (19L)' },
  { value: 'sayac2', label: 'Sayaç 2 (5L)' },
  { value: 'total', label: 'Toplam' },
];

const CHART_TYPE_OPTIONS = [
  { value: 'stacked-bar', label: 'Default Grafik' },
  { value: 'combo-all', label: 'Çift Eksen + % Değişim + Renk Kodlu + Değer Etiketleri' },
  { value: 'combo-dual', label: 'Çift Eksen' },
  { value: 'combo-percent', label: '% Değişim' },
  { value: 'combo-colors', label: 'Renk Kodlu' },
  { value: 'combo-labels', label: 'Değer Etiketleri' },
  { value: 'combo', label: 'Karma Grafik' },
  { value: 'line', label: 'Çizgi Grafiği' },
  { value: 'bar', label: 'Çubuk Grafiği' },
  { value: 'area', label: 'Alan Grafiği' },
];

export default function DeviceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const deviceId = params.id as string;

  const [devices, setDevices] = useState<DeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>(deviceId);
  const [chartData, setChartData] = useState<ChartResponse | null>(null);
  const [slotCount, setSlotCount] = useState<string>('30'); // Default: 1 ay (30 mum)
  const [period, setPeriod] = useState<string>('daily');
  const [metric, setMetric] = useState<string>('total');
  const [revenueChartType, setRevenueChartType] = useState('stacked-bar');
  const [deltaChartType, setDeltaChartType] = useState('bar');
  const [isLoading, setIsLoading] = useState(true);
  
  // Daily Revenue Table için ayrı state
  const [tablePeriod, setTablePeriod] = useState<string>('daily');
  const [tableData, setTableData] = useState<ChartResponse | null>(null);
  const [isTableLoading, setIsTableLoading] = useState(true);

  // Fetch all devices for the device selector
  useEffect(() => {
    const fetchDevices = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/api/v1/charts/devices/summary`);
        if (res.ok) {
          const data = await res.json();
          setDevices(data.devices || []);
        }
      } catch (error) {
        console.error('Failed to fetch devices:', error);
      }
    };
    fetchDevices();
  }, []);

  // Fetch chart data for Daily Revenue Table
  const fetchTableData = useCallback(async (selectedPeriod: string, selectedSlots: number) => {
    setIsTableLoading(true);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    try {
      const res = await fetch(
        `${apiUrl}/api/v1/charts/device/${selectedDeviceId}?period=${selectedPeriod}&slots=${selectedSlots}&metric=${metric}`
      );
      if (res.ok) {
        const data = await res.json();
        setTableData(data);
      }
    } catch (error) {
      console.error('Failed to fetch table data:', error);
    } finally {
      setIsTableLoading(false);
    }
  }, [selectedDeviceId, metric]);

  // Fetch chart data based on selected device
  const fetchChartData = useCallback(async (silent = false) => {
    if (!silent) {
      setIsLoading(true);
    }
    const selectedSlots = SLOT_OPTIONS.find(s => s.value === slotCount)?.slots || 30;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    try {
      const res = await fetch(
        `${apiUrl}/api/v1/charts/device/${selectedDeviceId}?period=${period}&slots=${selectedSlots}&metric=${metric}`
      );
      if (res.ok) {
        const data = await res.json();
        setChartData(data);
      }
    } catch (error) {
      console.error('Failed to fetch chart data:', error);
    } finally {
      if (!silent) {
        setIsLoading(false);
      }
    }
  }, [selectedDeviceId, period, slotCount, metric]);

  useEffect(() => {
    if (selectedDeviceId !== 'all') {
      fetchChartData();
    }
  }, [fetchChartData, selectedDeviceId]);

  // Otomatik sessiz yenileme: 60 saniyede bir verileri arka planda güncelle
  useEffect(() => {
    if (!selectedDeviceId || selectedDeviceId === 'all') return;

    const interval = setInterval(async () => {
      // Cihaz listesini de sessizce güncelle
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/api/v1/charts/devices/summary`);
        if (res.ok) {
          const data = await res.json();
          setDevices(data.devices || []);
        }
      } catch (error) {
        console.error('Silent device refresh failed:', error);
      }
      // Grafik verilerini sessizce güncelle
      fetchChartData(true); // silent=true: loading gösterme
    }, 60000); // 60 saniye (1 dakika)

    return () => clearInterval(interval);
  }, [fetchChartData, selectedDeviceId]);

  // Update table data when tablePeriod changes
  useEffect(() => {
    if (selectedDeviceId && selectedDeviceId !== 'all') {
      const selectedSlots = SLOT_OPTIONS.find(s => s.value === slotCount)?.slots || 30;
      fetchTableData(tablePeriod, selectedSlots);
    }
  }, [tablePeriod, selectedDeviceId, fetchTableData, slotCount]);

  // Handle device change
  const handleDeviceChange = (newDeviceId: string) => {
    setSelectedDeviceId(newDeviceId);
    if (newDeviceId === 'all') {
      router.push('/devices/all-devices', { scroll: false });
    } else {
      router.push(`/devices/${newDeviceId}`, { scroll: false });
    }
  };

  // Device info
  const deviceName = chartData?.device_name || (selectedDeviceId === 'all' ? 'Tüm Cihazlar' : `Cihaz ${selectedDeviceId}`);
  const lastDataPoint = chartData?.data?.[chartData.data.length - 1];
  const isOnline = lastDataPoint ? !lastDataPoint.is_offline : false;
  const lastSeen = lastDataPoint?.timestamp || '';

  // Current labels
  const currentMetricLabel = METRIC_OPTIONS.find(m => m.value === metric)?.label || 'Toplam';
  const currentPeriodLabel = PERIOD_OPTIONS.find(p => p.value === period)?.label || 'Günlük';
  const currentSlotLabel = SLOT_OPTIONS.find(s => s.value === slotCount)?.label || '1 Ay';
  const currentSlotCount = SLOT_OPTIONS.find(s => s.value === slotCount)?.slots || 30;

  // Prepare chart data
  const totalRevenueData = chartData?.data?.map((d) => ({
    ...d,
    value: d.total_value,
    value_19l: d.total_value_19l ?? 0,
    value_5l: d.total_value_5l ?? 0,
  })) || [];

  const deltaData = chartData?.data?.map((d, i) => ({
    ...d,
    value: d.delta,
    value_19l: d.delta_19l ?? 0,
    value_5l: d.delta_5l ?? 0,
    trend: d.delta > 0 ? (i > 0 && d.delta >= (chartData.data[i - 1]?.delta || 0) ? 'up' : 'stable') : 'zero',
  })) || [];

  const avgDelta = chartData?.summary?.avg_delta || 0;

  // Compute totals for "Tüm Cihazlar" summary card
  const totalAllDevices = devices.reduce((sum, d) => sum + d.total, 0);
  const onlineCount = devices.filter(d => d.is_online).length;
  const offlineCount = devices.filter(d => !d.is_online).length;

  // Helper: render chart
  const renderChart = (
    data: typeof totalRevenueData,
    chartType: string,
    colorKey: 'primary' | 'success',
    tooltipLabel: string,
    gradientId: string,
    showReferenceLine?: boolean
  ) => {
    if (data.length === 0) {
      return (
        <div className="h-[350px] flex items-center justify-center text-muted-foreground">
          Veri yok
        </div>
      );
    }

    const gradientColor = colorKey === 'primary' ? CHART_COLORS.primary : CHART_COLORS.success;
    const commonXAxis = <XAxis dataKey="label" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} angle={-45} textAnchor="end" height={60} />;
    const commonYAxis = <YAxis tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toString()} />;
    const commonGrid = <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />;
    const commonTooltip = <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '13px' }} formatter={(value: number) => [formatMoney(value), tooltipLabel]} labelFormatter={(label: string) => `Periyot: ${label}`} />;
    const refLine = showReferenceLine && avgDelta > 0 ? <ReferenceLine y={avgDelta} stroke="hsl(var(--muted-foreground))" strokeDasharray="5 5" label={{ value: `Ort: ${formatMoney(avgDelta)}`, position: 'insideTopRight', fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} /> : null;

    switch (chartType) {
      case 'stacked-bar': {
        const stackTooltip = (
          <Tooltip
            contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '13px' }}
            formatter={(value: number, name: string) => {
              const label = name === 'value_19l' ? '19L Ciro' : name === 'value_5l' ? '5L Ciro' : tooltipLabel;
              return [formatMoney(value), label];
            }}
            labelFormatter={(label: string) => `Periyot: ${label}`}
          />
        );
        const renderStackedLabel = (props: any) => {
          const { x = 0, y = 0, width = 0, value = 0 } = props;
          if (!value || value <= 0) return <g />;
          const label = value >= 1000 ? `${(value / 1000).toFixed(1)}k` : value.toFixed(0);
          const textX = x + width / 2;
          const textY = y - 8;
          return (
            <g>
              <text x={textX} y={textY} textAnchor="middle" fill="hsl(var(--muted-foreground))" fontSize={12} fontWeight={600}>{label}</text>
            </g>
          );
        };
        
        const renderInsideLabel = (props: any) => {
          const { x = 0, y = 0, width = 0, height = 0, value = 0, dataKey = '' } = props;
          if (!value || value <= 0) return <g />;
          const label = value >= 1000 ? `${(value / 1000).toFixed(1)}k` : value.toFixed(0);
          const textX = x + width / 2;
          const textY = y + height / 2 + 4;
          // 19L (mavi bar) için açık renk, 5L (yeşil bar) için koyu renk
          const textColor = dataKey === 'value_19l' ? '#e0f2fe' : '#14532d';
          return (
            <text x={textX} y={textY} textAnchor="middle" fill={textColor} fontSize={11} fontWeight={700}>{label}</text>
          );
        };
        return (
          <ResponsiveContainer width="100%" height={350}>
            <ComposedChart data={data} margin={{ top: 30, right: 30, left: 0, bottom: 30 }}>
              {commonGrid}{commonXAxis}{commonYAxis}{stackTooltip}
              <Legend formatter={(value) => value === 'value_19l' ? '19L Ciro' : value === 'value_5l' ? '5L Ciro' : 'Trend'} />
              <Bar dataKey="value_19l" stackId="stack" fill={CHART_COLORS.primary} radius={[0, 0, 0, 0]} maxBarSize={50} name="value_19l">
                <LabelList
                  dataKey="value_19l"
                  position="middle"
                  content={renderInsideLabel}
                />
              </Bar>
              <Bar dataKey="value_5l" stackId="stack" fill={CHART_COLORS.success} radius={[4, 4, 0, 0]} maxBarSize={50} name="value_5l">
                <LabelList
                  dataKey="value_5l"
                  position="middle"
                  content={renderInsideLabel}
                />
                <LabelList
                  dataKey="value"
                  position="top"
                  content={renderStackedLabel}
                />
              </Bar>
              <Line type="monotone" dataKey="value" stroke="#f97316" strokeWidth={3} dot={false} name="Trend" />
            </ComposedChart>
          </ResponsiveContainer>
        );
      }
      case 'area':
        return (
          <ResponsiveContainer width="100%" height={350}>
            <AreaChart data={data}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={gradientColor} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={gradientColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              {commonGrid}{commonXAxis}{commonYAxis}{commonTooltip}{refLine}
              <Area type="monotone" dataKey="value" stroke={gradientColor} strokeWidth={2} fill={`url(#${gradientId})`} />
            </AreaChart>
          </ResponsiveContainer>
        );
      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={data}>
              {commonGrid}{commonXAxis}{commonYAxis}{commonTooltip}{refLine}
              {showReferenceLine ? (
                <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={50}>
                   {data.map((entry, index) => (
                     <Cell key={`cell-${index}`} fill={entry.value === 0 ? 'hsl(var(--muted))' : entry.value >= avgDelta ? CHART_COLORS.success : CHART_COLORS.warning || '#f59e0b'} />
                   ))}
                 </Bar>
               ) : (
                 <Bar dataKey="value" fill={gradientColor} radius={[4, 4, 0, 0]} maxBarSize={50} />
              )}
            </BarChart>
          </ResponsiveContainer>
        );
      case 'line':
        return (
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={data}>
              {commonGrid}{commonXAxis}{commonYAxis}{commonTooltip}{refLine}
              <Line type="monotone" dataKey="value" stroke={gradientColor} strokeWidth={2} dot={{ fill: gradientColor, r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        );
      case 'combo':
        return (
          <ResponsiveContainer width="100%" height={350}>
            <ComposedChart data={data}>
              {commonGrid}{commonXAxis}{commonYAxis}{commonTooltip}{refLine}
              {showReferenceLine ? (
                <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={50}>
                  {data.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.value === 0 ? 'hsl(var(--muted))' : entry.value >= avgDelta ? CHART_COLORS.success : CHART_COLORS.warning || '#f59e0b'} />
                  ))}
                </Bar>
              ) : (
                <Bar dataKey="value" fill={gradientColor} radius={[4, 4, 0, 0]} maxBarSize={50} />
              )}
              <Line type="monotone" dataKey="value" stroke={CHART_COLORS.accent} strokeWidth={2} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        );
      case 'combo-labels': {
        const avgValue = data.reduce((sum, d) => sum + d.value, 0) / data.length;
        return (
          <ResponsiveContainer width="100%" height={350}>
            <ComposedChart data={data} margin={{ top: 50, right: 30, left: 0, bottom: 30 }}>
              {commonGrid}{commonXAxis}
              <YAxis yAxisId="left" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toString()} />
              {commonTooltip}
              <Bar dataKey="value" yAxisId="left" fill={gradientColor} radius={[4, 4, 0, 0]} maxBarSize={50}>
                <LabelList dataKey="value" position="top" formatter={(v: number) => v >= 1000 ? `${(v/1000).toFixed(1)}k` : v} style={{ fontSize: '11px', fill: 'hsl(var(--muted-foreground))' }} />
              </Bar>
              <Line type="monotone" dataKey="value" yAxisId="left" stroke={CHART_COLORS.accent} strokeWidth={2} dot={false} />
              <ReferenceLine y={avgValue} stroke="hsl(var(--muted-foreground))" strokeDasharray="5 5" yAxisId="left" />
            </ComposedChart>
          </ResponsiveContainer>
        );
      }
      case 'combo-dual': {
        const percentData = data.map((d, i) => {
          const prevValue = i > 0 ? data[i - 1].value : d.value;
          const percentChange = prevValue !== 0 ? ((d.value - prevValue) / prevValue) * 100 : 0;
          return { ...d, percentChange };
        });
        return (
          <ResponsiveContainer width="100%" height={350}>
            <ComposedChart data={percentData}>
              {commonGrid}{commonXAxis}
              <YAxis yAxisId="left" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toString()} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} tickFormatter={(v: number) => `${v.toFixed(1)}%`} />
              <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '13px' }} formatter={(value: number, name: string) => {
                if (name === 'percentChange') return [`${value.toFixed(1)}%`, '% Değişim'];
                return [formatMoney(value), tooltipLabel];
              }} labelFormatter={(label: string) => `Periyot: ${label}`} />
              <Bar dataKey="value" yAxisId="left" fill={gradientColor} radius={[4, 4, 0, 0]} maxBarSize={50} />
              <Line type="monotone" dataKey="percentChange" yAxisId="right" stroke={CHART_COLORS.accent} strokeWidth={2} dot={{ fill: CHART_COLORS.accent, r: 3 }} />
            </ComposedChart>
          </ResponsiveContainer>
        );
      }
      case 'combo-percent': {
        const percentData = data.map((d, i) => {
          const prevValue = i > 0 ? data[i - 1].value : d.value;
          const percentChange = prevValue !== 0 ? ((d.value - prevValue) / prevValue) * 100 : 0;
          return { ...d, percentChange };
        });
        return (
          <ResponsiveContainer width="100%" height={350}>
            <ComposedChart data={percentData}>
              {commonGrid}{commonXAxis}
              <YAxis yAxisId="left" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toString()} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} tickFormatter={(v: number) => `${v.toFixed(1)}%`} />
              <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '13px' }} formatter={(value: number, name: string) => {
                if (name === 'percentChange') return [`${value.toFixed(1)}%`, '% Değişim'];
                return [formatMoney(value), tooltipLabel];
              }} labelFormatter={(label: string) => `Periyot: ${label}`} />
              <Bar dataKey="value" yAxisId="left" fill={gradientColor} radius={[4, 4, 0, 0]} maxBarSize={50} />
              <Line type="monotone" dataKey="percentChange" yAxisId="right" stroke={CHART_COLORS.accent} strokeWidth={2} dot={{ fill: CHART_COLORS.accent, r: 3 }} />
            </ComposedChart>
          </ResponsiveContainer>
        );
      }
      case 'combo-colors': {
        const avgValue = data.reduce((sum, d) => sum + d.value, 0) / data.length;
        return (
          <ResponsiveContainer width="100%" height={350}>
            <ComposedChart data={data}>
              {commonGrid}{commonXAxis}
              <YAxis yAxisId="left" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toString()} />
              {commonTooltip}
              <Bar dataKey="value" yAxisId="left" radius={[4, 4, 0, 0]} maxBarSize={50}>
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.value === 0 ? 'hsl(var(--muted))' : entry.value >= avgValue ? CHART_COLORS.success : CHART_COLORS.warning || '#f59e0b'} />
                ))}
              </Bar>
              <Line type="monotone" dataKey="value" yAxisId="left" stroke={CHART_COLORS.accent} strokeWidth={2} dot={false} />
              <ReferenceLine y={avgValue} stroke="hsl(var(--muted-foreground))" strokeDasharray="5 5" yAxisId="left" />
            </ComposedChart>
          </ResponsiveContainer>
        );
      }
      case 'combo-all': {
        const avgValue = data.reduce((sum, d) => sum + d.value, 0) / data.length;
        const percentData = data.map((d, i) => {
          const prevValue = i > 0 ? data[i - 1].value : d.value;
          const percentChange = prevValue !== 0 ? ((d.value - prevValue) / prevValue) * 100 : 0;
          return { ...d, percentChange };
        });
        return (
          <ResponsiveContainer width="100%" height={350}>
            <ComposedChart data={percentData} margin={{ top: 50, right: 30, left: 0, bottom: 30 }}>
              {commonGrid}{commonXAxis}
              <YAxis yAxisId="left" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toString()} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} tickFormatter={(v: number) => `${v.toFixed(1)}%`} />
              <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '13px' }} formatter={(value: number, name: string) => {
                if (name === 'percentChange') return [`${value.toFixed(1)}%`, '% Değişim'];
                return [formatMoney(value), tooltipLabel];
              }} labelFormatter={(label: string) => `Periyot: ${label}`} />
              <Bar dataKey="value" yAxisId="left" radius={[4, 4, 0, 0]} maxBarSize={50}>
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.value === 0 ? 'hsl(var(--muted))' : entry.value >= avgValue ? CHART_COLORS.success : CHART_COLORS.warning || '#f59e0b'} />
                ))}
                <LabelList dataKey="value" position="top" formatter={(v: number) => v >= 1000 ? `${(v/1000).toFixed(1)}k` : v} style={{ fontSize: '11px', fill: 'hsl(var(--muted-foreground))' }} />
              </Bar>
              <Line type="monotone" dataKey="percentChange" yAxisId="right" stroke={CHART_COLORS.accent} strokeWidth={2} dot={{ fill: CHART_COLORS.accent, r: 3 }} />
              <ReferenceLine y={avgValue} stroke="hsl(var(--muted-foreground))" strokeDasharray="5 5" yAxisId="left" />
            </ComposedChart>
          </ResponsiveContainer>
        );
      }
      case 'area-labels': {
        const gradientId = `gradient-${chartType}`;
        return (
          <ResponsiveContainer width="100%" height={350}>
            <AreaChart data={data} margin={{ top: 50, right: 30, left: 0, bottom: 30 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.8}/>
                  <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              {commonGrid}
              {commonXAxis}
              <YAxis tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toString()} />
              <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '13px' }} formatter={(value: number) => [formatMoney(value), tooltipLabel]} labelFormatter={(label: string) => `Periyot: ${label}`} />
              <Area type="monotone" dataKey="value" stroke={CHART_COLORS.primary} strokeWidth={2} fill={`url(#${gradientId})`} />
              <LabelList dataKey="value" position="top" formatter={(v: number) => v >= 1000 ? `${(v/1000).toFixed(1)}k` : v} style={{ fontSize: '11px', fill: 'hsl(var(--muted-foreground))' }} />
            </AreaChart>
          </ResponsiveContainer>
        );
      }
      case 'area-dual': {
        const percentData = data.map((d, i) => {
          const prevValue = i > 0 ? data[i - 1].value : d.value;
          const percentChange = prevValue !== 0 ? ((d.value - prevValue) / prevValue) * 100 : 0;
          return { ...d, percentChange };
        });
        const gradientId = `gradient-${chartType}`;
        return (
          <ResponsiveContainer width="100%" height={350}>
            <ComposedChart data={percentData}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.8}/>
                  <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              {commonGrid}
              {commonXAxis}
              <YAxis yAxisId="left" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toString()} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} tickFormatter={(v: number) => `${v.toFixed(1)}%`} />
              <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '13px' }} formatter={(value: number, name: string) => {
                if (name === 'percentChange') return [`${value.toFixed(1)}%`, '% Değişim'];
                return [formatMoney(value), tooltipLabel];
              }} labelFormatter={(label: string) => `Periyot: ${label}`} />
              <Area type="monotone" dataKey="value" yAxisId="left" stroke={CHART_COLORS.primary} strokeWidth={2} fill={`url(#${gradientId})`} />
              <Line type="monotone" dataKey="percentChange" yAxisId="right" stroke={CHART_COLORS.accent} strokeWidth={2} dot={{ fill: CHART_COLORS.accent, r: 3 }} />
            </ComposedChart>
          </ResponsiveContainer>
        );
      }
      case 'area-percent': {
        const percentData = data.map((d, i) => {
          const prevValue = i > 0 ? data[i - 1].value : d.value;
          const percentChange = prevValue !== 0 ? ((d.value - prevValue) / prevValue) * 100 : 0;
          return { ...d, percentChange };
        });
        const gradientId = `gradient-${chartType}`;
        return (
          <ResponsiveContainer width="100%" height={350}>
            <ComposedChart data={percentData}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.8}/>
                  <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              {commonGrid}
              {commonXAxis}
              <YAxis yAxisId="left" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toString()} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} tickFormatter={(v: number) => `${v.toFixed(1)}%`} />
              <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '13px' }} formatter={(value: number, name: string) => {
                if (name === 'percentChange') return [`${value.toFixed(1)}%`, '% Değişim'];
                return [formatMoney(value), tooltipLabel];
              }} labelFormatter={(label: string) => `Periyot: ${label}`} />
              <Area type="monotone" dataKey="value" yAxisId="left" stroke={CHART_COLORS.primary} strokeWidth={2} fill={`url(#${gradientId})`} />
              <Line type="monotone" dataKey="percentChange" yAxisId="right" stroke={CHART_COLORS.accent} strokeWidth={2} dot={{ fill: CHART_COLORS.accent, r: 3 }} />
              <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" strokeDasharray="5 5" yAxisId="right" />
            </ComposedChart>
          </ResponsiveContainer>
        );
      }
      case 'area-all': {
        const avgValue = data.reduce((sum, d) => sum + d.value, 0) / data.length;
        const percentData = data.map((d, i) => {
          const prevValue = i > 0 ? data[i - 1].value : d.value;
          const percentChange = prevValue !== 0 ? ((d.value - prevValue) / prevValue) * 100 : 0;
          return { ...d, percentChange };
        });
        const gradientId = `gradient-${chartType}`;
        return (
          <ResponsiveContainer width="100%" height={350}>
            <ComposedChart data={percentData}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.8}/>
                  <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              {commonGrid}
              {commonXAxis}
              <YAxis yAxisId="left" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toString()} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} tickFormatter={(v: number) => `${v.toFixed(1)}%`} />
              <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '13px' }} formatter={(value: number, name: string) => {
                if (name === 'percentChange') return [`${value.toFixed(1)}%`, '% Değişim'];
                return [formatMoney(value), tooltipLabel];
              }} labelFormatter={(label: string) => `Periyot: ${label}`} />
              <Area type="monotone" dataKey="value" yAxisId="left" stroke={CHART_COLORS.primary} strokeWidth={2} fill={`url(#${gradientId})`} />
              <Line type="monotone" dataKey="percentChange" yAxisId="right" stroke={CHART_COLORS.accent} strokeWidth={2} dot={{ fill: CHART_COLORS.accent, r: 3 }} />
              <ReferenceLine y={avgValue} stroke="hsl(var(--muted-foreground))" strokeDasharray="5 5" yAxisId="left" />
              <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" strokeDasharray="5 5" yAxisId="right" />
            </ComposedChart>
          </ResponsiveContainer>
        );
      }
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push('/devices')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold tracking-tight">{deviceName}</h1>
              {selectedDeviceId !== 'all' && (
                <Badge variant={isOnline ? 'success' : 'destructive'}>
                  {isOnline ? (
                    <><Wifi className="mr-1 h-3 w-3" /> Çevrimiçi</>
                  ) : (
                    <><WifiOff className="mr-1 h-3 w-3" /> Çevrimdışı</>
                  )}
                </Badge>
              )}
            </div>
            <p className="text-muted-foreground flex items-center gap-2 text-sm">
              <MapPin className="h-3.5 w-3.5" />
              {selectedDeviceId === 'all'
                ? `${devices.length} cihazın birleşik özeti`
                : `Cihaz #${selectedDeviceId}`}
              {lastSeen && ` · Son veri: ${formatDate(lastSeen)}`}
            </p>
          </div>
        </div>
      </div>

      {/* Device Quick Selector - Card Grid */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Monitor className="h-4 w-4" />
            Cihaz Seçimi
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {/* "Tüm Cihazlar" Button */}
            <button
              onClick={() => handleDeviceChange('all')}
              className={`p-3 rounded-lg border-2 transition-all min-w-[120px] hover:shadow-md ${
                selectedDeviceId === 'all'
                  ? 'border-primary bg-primary/10 shadow-md ring-2 ring-primary/20'
                  : 'border-border hover:border-primary/50 bg-background'
              }`}
            >
              <div className="text-center">
                <div className="text-xs font-bold text-primary">TÜM CİHAZLAR</div>
                <div className="text-lg font-bold mt-1">{formatMoney(totalAllDevices)}</div>
                <div className="text-xs text-muted-foreground">
                  {onlineCount} aktif · {offlineCount} pasif
                </div>
              </div>
            </button>

            {/* Individual Device Buttons */}
            {devices.map((device) => (
              <button
                key={device.id}
                onClick={() => handleDeviceChange(device.id.toString())}
                className={`p-3 rounded-lg border-2 transition-all min-w-[120px] hover:shadow-md ${
                  selectedDeviceId === device.id.toString()
                    ? 'border-primary bg-primary/10 shadow-md ring-2 ring-primary/20'
                    : 'border-border hover:border-primary/50 bg-background'
                }`}
              >
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <span className={`inline-block w-2 h-2 rounded-full ${
                      device.is_online ? 'bg-green-500' : 'bg-red-500'
                    }`} />
                    <span className="font-bold text-xs">{device.device_code}</span>
                  </div>
                  <div className="text-xs text-muted-foreground truncate max-w-[100px]">{device.name}</div>
                  <div className="text-sm font-bold mt-1">{formatMoney(device.total)}</div>
                </div>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Süre & Periyot & Metrik Selectors */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium">Süre:</label>
          <div className="flex gap-1">
            {SLOT_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setSlotCount(opt.value)}
                className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
                  slotCount === opt.value
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-background hover:bg-muted border-border'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium">Periyot:</label>
          <div className="flex gap-1">
            {PERIOD_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setPeriod(opt.value)}
                className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
                  period === opt.value
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-background hover:bg-muted border-border'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
        {selectedDeviceId !== 'all' && (
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium">Metrik:</label>
            <div className="flex gap-1">
              {METRIC_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setMetric(opt.value)}
                  className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
                    metric === opt.value
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'bg-background hover:bg-muted border-border'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Toplam Ciro Chart */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary" />
              <div>
                <CardTitle className="text-base">
                  Toplam Ciro {selectedDeviceId !== 'all' ? `— ${currentMetricLabel}` : '— Tüm Cihazlar'}
                </CardTitle>
                <CardDescription>Son {currentSlotLabel} ({currentSlotCount} mum) · {currentPeriodLabel.toLowerCase()} periyot · Toplam kümülatif ciro: {formatMoney(selectedDeviceId === 'all' ? totalAllDevices : (chartData?.summary?.current_value || 0))}</CardDescription>
              </div>
            </div>
            <Select value={revenueChartType} onValueChange={setRevenueChartType}>
              <SelectTrigger className="w-[150px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CHART_TYPE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {/* Toplam Ciro Metrik Başlığı */}
          {!isLoading && (
            <ChartMetricsHeader
              type="revenue"
              metrics={{
                totalRevenue: selectedDeviceId === 'all' ? totalAllDevices : (chartData?.summary?.current_value || 0),
                revenue19l: chartData?.monthly_revenue_19l || 0,
                revenue5l: chartData?.monthly_revenue_5l || 0,
              }}
            />
          )}
          {isLoading ? (
            <div className="h-[350px] flex items-center justify-center text-muted-foreground">Yükleniyor...</div>
          ) : (
            renderChart(totalRevenueData, revenueChartType, 'primary', 'Toplam Ciro', 'colorRevenue')
          )}
        </CardContent>
      </Card>

      {/* Periyodik Artış Chart */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <LineChartIcon className="h-5 w-5 text-green-600" />
              <div>
                <CardTitle className="text-base">
                  Periyodik Artış {selectedDeviceId !== 'all' ? `— ${currentMetricLabel}` : '— Tüm Cihazlar'}
                </CardTitle>
                <CardDescription>
                  Son {currentSlotLabel} ({currentSlotCount} mum) · {currentPeriodLabel.toLowerCase()} periyot · Sadece artış değerleri
                </CardDescription>
              </div>
            </div>
            <Select value={deltaChartType} onValueChange={setDeltaChartType}>
              <SelectTrigger className="w-[150px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CHART_TYPE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {/* Periyodik Artış Metrik Başlığı */}
          {!isLoading && (() => {
            const lastDelta = deltaData.length > 0 ? deltaData[deltaData.length - 1].value : 0;
            const prevDelta = deltaData.length > 1 ? deltaData[deltaData.length - 2].value : 0;
            const change = lastDelta - prevDelta;
            return (
              <ChartMetricsHeader
                type="delta"
                metrics={{
                  lastPeriod: lastDelta,
                  change: change,
                  min: chartData?.summary?.min_delta || 0,
                  max: chartData?.summary?.max_delta || 0,
                  avg: chartData?.summary?.avg_delta || 0,
                }}
              />
            );
          })()}
          {isLoading ? (
            <div className="h-[350px] flex items-center justify-center text-muted-foreground">Yükleniyor...</div>
          ) : (
            renderChart(deltaData, deltaChartType, 'success', 'Artış', 'colorDelta', true)
          )}
       </CardContent>
     </Card>

     {/* Daily Revenue Table — Zaman Bazlı Ciro Tablosu */}
     <Card>
       <CardContent className="pt-6">
         <div className="flex items-center justify-between mb-4">
           <div>
             <h3 className="text-lg font-semibold">{PERIOD_OPTIONS.find(p => p.value === tablePeriod)?.label || 'Günlük'} Ciro Tablosu</h3>
             <p className="text-sm text-muted-foreground">{PERIOD_OPTIONS.find(p => p.value === tablePeriod)?.label || 'Günlük'} toplam ciro, artış ve durum bilgileri</p>
           </div>
           <div className="flex gap-1">
             {PERIOD_OPTIONS.map((opt) => (
               <button
                 key={opt.value}
                 onClick={() => setTablePeriod(opt.value)}
                 className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
                   tablePeriod === opt.value
                     ? 'bg-primary text-primary-foreground border-primary'
                     : 'bg-background hover:bg-muted border-border'
                 }`}
               >
                 {opt.label}
               </button>
             ))}
           </div>
         </div>
         <DailyRevenueTable
           data={(tableData?.data ?? []) as any}
           isLoading={isTableLoading}
           timeRange={SLOT_OPTIONS.find(s => s.value === slotCount)?.slots || 30}
           period={tablePeriod}
         />
       </CardContent>
     </Card>

    </div>
  );
}
