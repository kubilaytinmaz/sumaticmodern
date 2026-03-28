'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { DollarSign, Monitor, TrendingUp, Activity, RefreshCw, AlertCircle, Calendar, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { RealtimeIndicator } from '@/components/dashboard/RealtimeIndicator';
import { RevenueChart } from '@/components/dashboard/RevenueChart';
import { CumulativeComparisonChart } from '@/components/dashboard/CumulativeComparisonChart';
import type { ChartType } from '@/components/dashboard/RevenueChart';
import type { CumulativeComparisonData } from '@/components/dashboard/CumulativeComparisonChart';
import { useWebSocket } from '@/hooks/useWebSocket';
import { formatMoney } from '@/lib/utils';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const REFRESH_INTERVAL = 30000; // 30 seconds

// API Response Types
interface DeviceOfflineInfo {
  device_id: number;
  device_name: string;
  offline_hours: number;
}

interface MonthlyStatsResponse {
  month: string;
  month_name: string;
  last_day_revenue: number;
  yesterday_revenue: number;
  max_day_revenue: number;
  max_day_date: string;
  avg_daily_revenue: number;
  total_month_revenue: number;
  daily_offline_hours_yesterday: number;
  total_devices: number;
  active_devices: number;
  device_offline_hours: DeviceOfflineInfo[];
}

interface DailyBreakdown {
  date: string;
  date_label: string;
  counter_19l: number;
  counter_5l: number;
  revenue: number;
  devices_with_data_count: number;
  devices_without_data_count: number;
  offline_hours: number;
}

interface MonthlyBreakdownResponse {
  year: number;
  month: number;
  month_start: string;
  month_end: string;
  daily_data: DailyBreakdown[];
  total_month_revenue: number;
  avg_daily_revenue: number;
  max_day_revenue: number;
  max_day_date: string;
}

// Generate month options starting from January 2026 with future months
function generateMonthOptions(): Array<{ value: string; label: string; year: number; month: number }> {
  const options: Array<{ value: string; label: string; year: number; month: number }> = [];
  const monthNames = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];
  
  // Start from January 2026 and go forward for 24 months (2 years)
  let date = new Date(2026, 0, 1);
  for (let i = 0; i < 24; i++) {
    options.push({
      value: `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`,
      label: `${monthNames[date.getMonth()]} ${date.getFullYear()}`,
      year: date.getFullYear(),
      month: date.getMonth() + 1,
    });
    // Move to next month
    date = new Date(date.getFullYear(), date.getMonth() + 1, 1);
  }
  return options;
}

// Get current month in YYYY-MM format
function getCurrentMonthValue(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

// Get previous month in YYYY-MM format
function getPreviousMonthValue(): string {
  const now = new Date();
  const prevMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  return `${prevMonth.getFullYear()}-${String(prevMonth.getMonth() + 1).padStart(2, '0')}`;
}

// RevenueChart veri formatına dönüştür
function transformBreakdownToChartData(breakdown: MonthlyBreakdownResponse) {
  return breakdown.daily_data.map((day) => ({
    name: day.date_label,
    '19L': day.counter_19l,
    '5L': day.counter_5l,
    total: day.counter_19l + day.counter_5l,
  }));
}

export default function DashboardPage() {
  const router = useRouter();
  const { isConnected } = useWebSocket();

  // State
  const [selectedMonth, setSelectedMonth] = useState<string>('');
  const [monthlyStats, setMonthlyStats] = useState<MonthlyStatsResponse | null>(null);
  const [monthlyBreakdown, setMonthlyBreakdown] = useState<MonthlyBreakdownResponse | null>(null);
  const [chartType, setChartType] = useState<ChartType>('composed');
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Cumulative comparison state
  const [selectedMonth1, setSelectedMonth1] = useState<string>('');
  const [selectedMonth2, setSelectedMonth2] = useState<string>('');
  const [cumulativeData, setCumulativeData] = useState<CumulativeComparisonData | null>(null);
  const [isLoadingCumulative, setIsLoadingCumulative] = useState(false);

  const monthOptions = useMemo(() => generateMonthOptions(), []);

  // Initialize with current month (this month)
  useEffect(() => {
    if (!selectedMonth && monthOptions.length > 0) {
      const currentMonth = getCurrentMonthValue();
      // Check if current month exists in options
      const exists = monthOptions.some(m => m.value === currentMonth);
      setSelectedMonth(exists ? currentMonth : monthOptions[0].value);
    }
  }, [monthOptions, selectedMonth]);

  // Initialize cumulative comparison with current month and previous month
  useEffect(() => {
    if (monthOptions.length >= 2 && !selectedMonth1 && !selectedMonth2) {
      const currentMonth = getCurrentMonthValue();
      const previousMonth = getPreviousMonthValue();
      
      // Check if both months exist in options
      const currentExists = monthOptions.some(m => m.value === currentMonth);
      const previousExists = monthOptions.some(m => m.value === previousMonth);
      
      setSelectedMonth1(currentExists ? currentMonth : monthOptions[0].value);
      setSelectedMonth2(previousExists ? previousMonth : monthOptions[1].value);
    }
  }, [monthOptions.length]);

  // Fetch monthly stats
  const fetchMonthlyStats = useCallback(async (year: number, month: number) => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/charts/devices/monthly-stats?year=${year}&month=${month}`
      );
      if (!response.ok) throw new Error('Aylık istatistikler alınamadı');
      return await response.json();
    } catch (err) {
      console.error('Failed to fetch monthly stats:', err);
      throw err;
    }
  }, []);

  // Fetch monthly breakdown (günlük detay verileri)
  const fetchMonthlyBreakdown = useCallback(async (year: number, month: number) => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/charts/devices/monthly-breakdown?year=${year}&month=${month}`
      );
      if (!response.ok) throw new Error('Aylık detay alınamadı');
      return await response.json();
    } catch (err) {
      console.error('Failed to fetch monthly breakdown:', err);
      throw err;
    }
  }, []);

  // Fetch cumulative comparison data
  const fetchCumulativeComparison = useCallback(async () => {
    if (!selectedMonth1 || !selectedMonth2) return;

    setIsLoadingCumulative(true);
    try {
      const option1 = monthOptions.find(m => m.value === selectedMonth1);
      const option2 = monthOptions.find(m => m.value === selectedMonth2);
      
      if (!option1 || !option2) return;

      console.log('Fetching cumulative comparison:', { option1, option2 });
      const response = await fetch(
        `${API_BASE_URL}/api/v1/charts/devices/monthly-cumulative-comparison?year1=${option1.year}&month1=${option1.month}&year2=${option2.year}&month2=${option2.month}`
      );
      
      if (!response.ok) throw new Error('Kümülatif karşılaştırma verileri alınamadı');
      const data = await response.json();
      console.log('Cumulative comparison data received:', data);
      console.log('Month 1 data length:', data.month1_data?.length);
      console.log('Month 2 data length:', data.month2_data?.length);
      console.log('Month 1 total:', data.month1_total);
      console.log('Month 2 total:', data.month2_total);
      setCumulativeData(data);
    } catch (err) {
      console.error('Failed to fetch cumulative comparison:', err);
    } finally {
      setIsLoadingCumulative(false);
    }
  }, [selectedMonth1, selectedMonth2]);

  // Fetch cumulative data when months change
  useEffect(() => {
    fetchCumulativeComparison();
  }, [fetchCumulativeComparison]);

  // Fetch all data
  const fetchAllData = useCallback(async (showRefreshing = false) => {
    if (!selectedMonth) return;

    if (showRefreshing) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const selectedOption = monthOptions.find(m => m.value === selectedMonth);
      if (!selectedOption) return;

      const { year, month } = selectedOption;

      // Paralel fetch: monthly stats + monthly breakdown
      const [stats, breakdown] = await Promise.all([
        fetchMonthlyStats(year, month),
        fetchMonthlyBreakdown(year, month),
      ]);

      setMonthlyStats(stats);
      setMonthlyBreakdown(breakdown);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Veriler yüklenirken hata oluştu');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [selectedMonth, monthOptions, fetchMonthlyStats, fetchMonthlyBreakdown]);

  // Initial fetch and refetch on month change
  useEffect(() => {
    if (selectedMonth) {
      fetchAllData();
    }
  }, [selectedMonth]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-refresh
  useEffect(() => {
    const interval = setInterval(() => {
      fetchAllData(true);
    }, REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [fetchAllData]);

  // Handle manual refresh
  const handleRefresh = () => {
    fetchAllData(true);
  };

  // Handle month change
  const handleMonthChange = (value: string) => {
    setSelectedMonth(value);
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="h-9 w-48 bg-muted animate-pulse rounded" />
            <div className="h-5 w-64 bg-muted animate-pulse rounded mt-2" />
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <div className="h-4 w-24 bg-muted animate-pulse rounded mb-2" />
                <div className="h-8 w-32 bg-muted animate-pulse rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
        <Card>
          <CardContent className="pt-6">
            <div className="h-[400px] bg-muted animate-pulse rounded" />
          </CardContent>
        </Card>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground">
              Su otomatı ciro takip ve analiz sistemi
            </p>
          </div>
        </div>

        <Card className="border-destructive">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="h-12 w-12 text-destructive mb-4" />
            <h3 className="text-lg font-semibold mb-2">Veriler Yüklenemedi</h3>
            <p className="text-muted-foreground text-center mb-4">{error}</p>
            <Button onClick={handleRefresh}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Tekrar Dene
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Chart verisi
  const chartData = monthlyBreakdown ? transformBreakdownToChartData(monthlyBreakdown) : [];

  return (
    <div className="space-y-6">
      {/* Header with Month Selector */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Su Otomatları Uzak Takip
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Month Selector - Prominently displayed */}
          <div className="flex items-center gap-2 bg-card border border-input rounded-lg px-4 py-2">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <Select value={selectedMonth} onValueChange={handleMonthChange}>
              <SelectTrigger className="border-0 bg-transparent w-[200px] focus:ring-0">
                <SelectValue placeholder="Ay seçin" />
              </SelectTrigger>
              <SelectContent>
                {monthOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            {isRefreshing ? 'Yükleniyor...' : 'Yenile'}
          </Button>
          <RealtimeIndicator isConnected={isConnected} />
        </div>
      </div>

      {/* Monthly Stats Cards */}
      {monthlyStats && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Son Günün Cirosu
              </CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatMoney(monthlyStats.last_day_revenue)}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {monthlyStats.month_name}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Dünün Cirosu
              </CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatMoney(monthlyStats.yesterday_revenue)}</div>
              <p className="text-xs text-muted-foreground mt-1">
                Dün
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                En İyi Gün
              </CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatMoney(monthlyStats.max_day_revenue)}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {monthlyStats.max_day_date}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Ortalama Günlük Kazanç
              </CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatMoney(monthlyStats.avg_daily_revenue)}</div>
              <p className="text-xs text-muted-foreground mt-1">
                Bu ay ortalama
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Device Status Summary */}
      {monthlyStats && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Toplam Cihaz
              </CardTitle>
              <Monitor className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{monthlyStats.total_devices}</div>
              <div className="flex items-center gap-4 mt-3">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-green-500" />
                  <span className="text-xs text-muted-foreground">{monthlyStats.active_devices} Aktif</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-red-500" />
                  <span className="text-xs text-muted-foreground">{monthlyStats.total_devices - monthlyStats.active_devices} Pasif</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Offline Süreleri
              </CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {monthlyStats.device_offline_hours && monthlyStats.device_offline_hours.length > 0 ? (
                <div className="space-y-2 mt-1">
                  {monthlyStats.device_offline_hours.map((device) => (
                    <div key={device.device_id} className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground truncate max-w-[140px]" title={device.device_name}>
                        {device.device_name}
                      </span>
                      <span className={`text-xs font-semibold ml-2 px-2 py-0.5 rounded-full whitespace-nowrap ${
                        device.offline_hours === 0
                          ? 'bg-green-500/10 text-green-600'
                          : device.offline_hours >= 48
                          ? 'bg-red-500/10 text-red-600'
                          : 'bg-orange-500/10 text-orange-600'
                      }`}>
                        {device.offline_hours.toFixed(0)} saat
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-2xl font-bold">
                  {monthlyStats.daily_offline_hours_yesterday.toFixed(1)}s
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {monthlyStats.month_name} Ciro
              </CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {formatMoney(monthlyStats.total_month_revenue)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Toplam aylık ciro
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Aylık Kümülatif Ciro Karşılaştırması */}
      {monthOptions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Aylık Kümülatif Ciro Karşılaştırması
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Month Selectors */}
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <label className="text-sm font-medium">1. Ay:</label>
                  <Select value={selectedMonth1} onValueChange={setSelectedMonth1}>
                    <SelectTrigger className="w-[180px]">
                      <SelectValue placeholder="Ay seçin" />
                    </SelectTrigger>
                    <SelectContent>
                      {monthOptions.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <label className="text-sm font-medium">2. Ay:</label>
                  <Select value={selectedMonth2} onValueChange={setSelectedMonth2}>
                    <SelectTrigger className="w-[180px]">
                      <SelectValue placeholder="Ay seçin" />
                    </SelectTrigger>
                    <SelectContent>
                      {monthOptions.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Chart */}
              {selectedMonth1 && selectedMonth2 && (
                <CumulativeComparisonChart
                  data={cumulativeData}
                  isLoading={isLoadingCumulative}
                />
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Günlük Ciro Trendi */}
      {monthlyBreakdown && chartData.length > 0 && (
        <RevenueChart
          data={chartData}
          title={`Günlük Ciro Trendi — ${monthlyStats?.month_name ?? ''}`}
          chartType={chartType}
          height={400}
          isLoading={isRefreshing}
          onChartTypeChange={setChartType}
        />
      )}

    </div>
  );
}
