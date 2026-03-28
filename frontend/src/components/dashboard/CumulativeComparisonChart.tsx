'use client';

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Skeleton } from '@/components/ui/skeleton';
import { formatMoney } from '@/lib/utils';
import { CHART_COLORS } from '@/lib/constants';

export interface CumulativeDataPoint {
  day: number;
  day_label: string;
  daily_revenue: number;
  cumulative_revenue: number;
}

export interface CumulativeComparisonData {
  month1_data: CumulativeDataPoint[];
  month2_data: CumulativeDataPoint[];
  month1_name: string;
  month2_name: string;
  month1_total: number;
  month2_total: number;
}

interface CumulativeComparisonChartProps {
  data: CumulativeComparisonData | null;
  isLoading?: boolean;
  height?: number;
}

// Ortak tooltip stili
const tooltipContentStyle = {
  backgroundColor: 'hsl(var(--card))',
  border: '1px solid hsl(var(--border))',
  borderRadius: '8px',
  color: 'hsl(var(--card-foreground))',
  fontSize: '12px',
  boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
};

// Ortak eksen tick stili
const axisTick = { fill: 'hsl(var(--muted-foreground))', fontSize: 11 };
const axisLine = { stroke: 'hsl(var(--border))' };

// Verileri birleştir - her ay için ayrı seriler
function mergeDataForChart(data: CumulativeComparisonData) {
  // Create a map of day number -> {cumulative_revenue, day_label} for each month
  const month1Map = new Map(data.month1_data.map(d => [d.day, d]));
  const month2Map = new Map(data.month2_data.map(d => [d.day, d]));
  
  // Bug 1 Fix: Get the max day number from month1 safely (check length before Math.max)
  const maxDay1 = data.month1_data.length > 0
    ? Math.max(...data.month1_data.map(d => d.day))
    : 0;
  
  // Bug 2 Fix: Get the last day with data for month2 - check if data exists, not if daily_revenue > 0
  // (carry-forward days have daily_revenue = 0 but are still valid cumulative data)
  const month2LastDay = data.month2_data.length > 0
    ? Math.max(...data.month2_data.map(d => d.day))
    : 0;
  
  // Bug 3 Fix: Calculate max day independently for each month
  // Month1 shows all available data
  const displayMaxDay1 = maxDay1;
  // Month2 shows only up to its last day
  const displayMaxDay2 = month2LastDay;
  // Use the max of both for display
  const displayMaxDay = Math.max(displayMaxDay1, displayMaxDay2);
  
  // Track last value for each month (carry-forward mechanism)
  let lastMonth1Value = 0;
  let lastMonth2Value = 0;
  
  // Create merged data by day number
  const mergedData = [];
  for (let day = 1; day <= displayMaxDay; day++) {
    // Get current data points
    const day1Data = month1Map.get(day);
    const day2Data = month2Map.get(day);
    
    // Update last value for month1 if we have data (carry-forward for month1)
    if (day1Data) lastMonth1Value = day1Data.cumulative_revenue;
    
    // Update last value for month2 if we have data (carry-forward for month2)
    if (day2Data) lastMonth2Value = day2Data.cumulative_revenue;
    
    // Get cumulative values
    // Month1: show carry-forward values up to its max day
    const month1Value = day <= displayMaxDay1 ? lastMonth1Value : null;
    // Month2: show carry-forward values up to its max day
    const month2Value = day <= displayMaxDay2 ? lastMonth2Value : null;
    
    // Create day label - show day number
    const dayLabel = `${day}. Gün`;
    
    mergedData.push({
      day: day,
      day_label: dayLabel,
      month1: month1Value,
      month2: month2Value,
    });
  }
  
  return mergedData;
}

export function CumulativeComparisonChart({
  data,
  isLoading = false,
  height = 400,
}: CumulativeComparisonChartProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center" style={{ height }}>
        <Skeleton className="w-full" style={{ height }} />
      </div>
    );
  }

  if (!data || (!data.month1_data.length && !data.month2_data.length)) {
    return (
      <div className="flex items-center justify-center" style={{ height }}>
        <p className="text-muted-foreground">Karşılaştırılacak veri bulunamadı</p>
      </div>
    );
  }

  const chartData = mergeDataForChart(data);
  
  // Bug 4 Fix: Also check if merged data is empty (both months had 0 days of data)
  if (!chartData || chartData.length === 0) {
    return (
      <div className="flex items-center justify-center" style={{ height }}>
        <p className="text-muted-foreground">Karşılaştırılacak veri bulunamadı</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with totals */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded"
              style={{ backgroundColor: CHART_COLORS.primary }}
            />
            <span className="text-muted-foreground">{data.month1_name}</span>
            <span className="font-semibold">{formatMoney(data.month1_total)}</span>
          </div>
          <div className="flex items-center gap-2">
            <div 
              className="w-3 h-3 rounded" 
              style={{ backgroundColor: CHART_COLORS.secondary }} 
            />
            <span className="text-muted-foreground">{data.month2_name}</span>
            <span className="font-semibold">{formatMoney(data.month2_total)}</span>
          </div>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart 
          data={chartData} 
          margin={{ top: 10, right: 30, left: 0, bottom: 30 }}
        >
          <defs>
            <linearGradient id="gradientMonth1" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.4} />
              <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="gradientMonth2" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={CHART_COLORS.secondary} stopOpacity={0.4} />
              <stop offset="95%" stopColor={CHART_COLORS.secondary} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.35} />
          <XAxis
            dataKey="day_label"
            tick={axisTick}
            axisLine={axisLine}
            tickLine={false}
            interval={0}
            minTickGap={5}
          />
          <YAxis 
            tick={axisTick} 
            axisLine={axisLine} 
            tickLine={false} 
            tickFormatter={(v) => `${v}`} 
            width={45} 
          />
          <Tooltip
            contentStyle={tooltipContentStyle}
            formatter={(value: number, name: string) => [formatMoney(value), name]}
            labelStyle={{ color: 'hsl(var(--card-foreground))', fontWeight: 600 }}
          />
          <Legend
            wrapperStyle={{ paddingTop: '10px', fontSize: '12px' }}
            formatter={(value) => <span style={{ color: 'hsl(var(--muted-foreground))' }}>{value}</span>}
          />
          <Area
            type="monotone"
            dataKey="month1"
            name={data.month1_name}
            stroke={CHART_COLORS.primary}
            strokeWidth={2}
            fill="url(#gradientMonth1)"
            dot={false}
            activeDot={{ r: 5, strokeWidth: 2 }}
          />
          <Area
            type="monotone"
            dataKey="month2"
            name={data.month2_name}
            stroke={CHART_COLORS.secondary}
            strokeWidth={2}
            fill="url(#gradientMonth2)"
            dot={false}
            activeDot={{ r: 5, strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
