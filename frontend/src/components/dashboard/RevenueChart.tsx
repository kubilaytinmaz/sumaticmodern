'use client';

import {
  BarChart,
  Bar,
  AreaChart,
  Area,
  LineChart,
  Line,
  ComposedChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
  LabelList,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { formatMoney } from '@/lib/utils';
import { CHART_COLORS } from '@/lib/constants';
import { BarChart2 } from 'lucide-react';

export type ChartType = 'bar' | 'area' | 'line' | 'composed';

interface RevenueData {
  name: string;
  '19L': number;
  '5L': number;
  total: number;
}

interface RevenueChartProps {
  data: RevenueData[];
  title?: string;
  isLoading?: boolean;
  height?: number;
  chartType?: ChartType;
  onChartTypeChange?: (type: ChartType) => void;
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

// Ortalama değer hesapla (reference line için)
function calcAverage(data: RevenueData[]): number {
  if (!data.length) return 0;
  const sum = data.reduce((acc, d) => acc + d.total, 0);
  return Math.round(sum / data.length);
}

// BarChart render
function renderBarChart(data: RevenueData[], height: number) {
  const avg = calcAverage(data);
  return (
    <BarChart data={data} margin={{ top: 50, right: 30, left: 0, bottom: 30 }}>
      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} />
      <XAxis
        dataKey="name"
        tick={axisTick}
        axisLine={axisLine}
        tickLine={false}
        interval={0}
        minTickGap={5}
        tickFormatter={(value) => {
          // Uzun etiketleri kısalt
          if (typeof value === 'string' && value.length > 10) {
            return value.substring(0, 8) + '...';
          }
          return value;
        }}
      />
      <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} tickFormatter={(v) => `${v}`} width={45} />
      <Tooltip
        contentStyle={tooltipContentStyle}
        formatter={(value: number, name: string) => [formatMoney(value), name]}
        labelStyle={{ color: 'hsl(var(--card-foreground))', fontWeight: 600 }}
      />
      <Legend
        wrapperStyle={{ paddingTop: '10px', fontSize: '12px' }}
        formatter={(value) => <span style={{ color: 'hsl(var(--muted-foreground))' }}>{value}</span>}
      />
      <Bar
        dataKey="19L"
        stackId="a"
        fill={CHART_COLORS.primary}
        radius={[0, 0, 0, 0]}
        maxBarSize={60}
        opacity={0.85}
      >
        <LabelList
          dataKey="19L"
          position="center"
          formatter={(value: number) => value > 0 ? formatMoney(value) : ''}
          style={{ fontSize: '11px', fill: '#ffffff', fontWeight: 600 }}
        />
      </Bar>
      <Bar
        dataKey="5L"
        stackId="a"
        fill={CHART_COLORS.success}
        radius={[4, 4, 0, 0]}
        maxBarSize={60}
        opacity={0.9}
      >
        <LabelList
          dataKey="5L"
          position="center"
          formatter={(value: number) => value > 0 ? formatMoney(value) : ''}
          style={{ fontSize: '11px', fill: '#ffffff', fontWeight: 600 }}
        />
        <LabelList
          dataKey="total"
          position="top"
          formatter={(value: number) => value > 0 ? formatMoney(value) : ''}
          style={{ fontSize: '12px', fill: 'hsl(var(--muted-foreground))', fontWeight: 700 }}
        />
      </Bar>
    </BarChart>
  );
}

// AreaChart render
function renderAreaChart(data: RevenueData[], height: number) {
  const avg = calcAverage(data);
  return (
    <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 30 }}>
      <defs>
        <linearGradient id="gradient19L" x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.4} />
          <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0.02} />
        </linearGradient>
        <linearGradient id="gradient5L" x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%" stopColor={CHART_COLORS.success} stopOpacity={0.5} />
          <stop offset="95%" stopColor={CHART_COLORS.success} stopOpacity={0.03} />
        </linearGradient>
      </defs>
      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.35} />
      <XAxis
        dataKey="name"
        tick={axisTick}
        axisLine={axisLine}
        tickLine={false}
        interval={0}
        minTickGap={5}
        tickFormatter={(value) => {
          if (typeof value === 'string' && value.length > 10) {
            return value.substring(0, 8) + '...';
          }
          return value;
        }}
      />
      <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} tickFormatter={(v) => `${v}`} width={45} />
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
        dataKey="19L"
        stackId="1"
        stroke={CHART_COLORS.primary}
        strokeWidth={2}
        fill="url(#gradient19L)"
        dot={false}
        activeDot={{ r: 5, strokeWidth: 2 }}
      />
      <Area
        type="monotone"
        dataKey="5L"
        stackId="1"
        stroke={CHART_COLORS.success}
        strokeWidth={2}
        fill="url(#gradient5L)"
        dot={false}
        activeDot={{ r: 5, strokeWidth: 2 }}
      />
    </AreaChart>
  );
}

// LineChart render
function renderLineChart(data: RevenueData[], height: number) {
  const avg = calcAverage(data);
  return (
    <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 30 }}>
      <defs>
        <linearGradient id="gradientTotal" x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%" stopColor={CHART_COLORS.primary} stopOpacity={0.15} />
          <stop offset="95%" stopColor={CHART_COLORS.primary} stopOpacity={0.0} />
        </linearGradient>
      </defs>
      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
      <XAxis
        dataKey="name"
        tick={axisTick}
        axisLine={axisLine}
        tickLine={false}
        interval={0}
        minTickGap={5}
        tickFormatter={(value) => {
          if (typeof value === 'string' && value.length > 10) {
            return value.substring(0, 8) + '...';
          }
          return value;
        }}
      />
      <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} tickFormatter={(v) => `${v}`} width={45} />
      <Tooltip
        contentStyle={tooltipContentStyle}
        formatter={(value: number, name: string) => [formatMoney(value), name]}
        labelStyle={{ color: 'hsl(var(--card-foreground))', fontWeight: 600 }}
      />
      <Legend
        wrapperStyle={{ paddingTop: '10px', fontSize: '12px' }}
        formatter={(value) => <span style={{ color: 'hsl(var(--muted-foreground))' }}>{value}</span>}
      />
      {/* Gölge alanı */}
      <Area
        type="monotone"
        dataKey="total"
        stroke="transparent"
        fill="url(#gradientTotal)"
        legendType="none"
      />
      <Line
        type="monotone"
        dataKey="19L"
        stroke={CHART_COLORS.primary}
        strokeWidth={2.5}
        dot={{ r: 3, fill: CHART_COLORS.primary, strokeWidth: 0 }}
        activeDot={{ r: 6, strokeWidth: 2, stroke: 'hsl(var(--background))' }}
      />
      <Line
        type="monotone"
        dataKey="5L"
        stroke={CHART_COLORS.success}
        strokeWidth={2.5}
        dot={{ r: 3, fill: CHART_COLORS.success, strokeWidth: 0 }}
        activeDot={{ r: 6, strokeWidth: 2, stroke: 'hsl(var(--background))' }}
        strokeDasharray="0"
      />
    </AreaChart>
  );
}

// ComposedChart render (Bar + Line combined)
function renderComposedChart(data: RevenueData[], height: number) {
  const avg = calcAverage(data);
  return (
    <ComposedChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 30 }}>
      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.35} />
      <XAxis
        dataKey="name"
        tick={axisTick}
        axisLine={axisLine}
        tickLine={false}
        interval={0}
        minTickGap={5}
        tickFormatter={(value) => {
          if (typeof value === 'string' && value.length > 10) {
            return value.substring(0, 8) + '...';
          }
          return value;
        }}
      />
      <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} tickFormatter={(v) => `${v}`} width={45} />
      <Tooltip
        contentStyle={tooltipContentStyle}
        formatter={(value: number, name: string) => [formatMoney(value), name]}
        labelStyle={{ color: 'hsl(var(--card-foreground))', fontWeight: 600 }}
      />
      <Legend
        wrapperStyle={{ paddingTop: '10px', fontSize: '12px' }}
        formatter={(value) => <span style={{ color: 'hsl(var(--muted-foreground))' }}>{value}</span>}
      />
      <Bar
        dataKey="19L"
        stackId="a"
        fill={CHART_COLORS.primary}
        radius={[0, 0, 0, 0]}
        maxBarSize={55}
      >
        <LabelList
          dataKey="19L"
          position="center"
          formatter={(value: number) => value > 0 ? formatMoney(value) : ''}
          style={{ fontSize: '11px', fill: '#ffffff', fontWeight: 600 }}
        />
      </Bar>
      <Bar
        dataKey="5L"
        stackId="a"
        fill={CHART_COLORS.success}
        radius={[3, 3, 0, 0]}
        maxBarSize={55}
      >
        <LabelList
          dataKey="5L"
          position="center"
          formatter={(value: number) => value > 0 ? formatMoney(value) : ''}
          style={{ fontSize: '11px', fill: '#ffffff', fontWeight: 600 }}
        />
        <LabelList
          dataKey="total"
          position="top"
          formatter={(value: number) => value > 0 ? formatMoney(value) : ''}
          style={{ fontSize: '10px', fill: 'hsl(var(--muted-foreground))', fontWeight: 500 }}
        />
      </Bar>
      <Line
        type="monotone"
        dataKey="total"
        name="Toplam (trend)"
        stroke="#f97316"
        strokeWidth={2.5}
        dot={{ r: 3, fill: '#f97316', strokeWidth: 0 }}
        activeDot={{ r: 6, strokeWidth: 2, stroke: 'hsl(var(--background))' }}
      />
    </ComposedChart>
  );
}

export function RevenueChart({
  data,
  title = 'Gelir Dağılımı',
  isLoading = false,
  height = 300,
  chartType = 'bar',
  onChartTypeChange,
}: RevenueChartProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-32" />
        </CardHeader>
        <CardContent>
          <Skeleton className="w-full" style={{ height }} />
        </CardContent>
      </Card>
    );
  }

  const renderChart = () => {
    switch (chartType) {
      case 'area':
        return renderAreaChart(data, height);
      case 'line':
        return renderLineChart(data, height);
      case 'composed':
        return renderComposedChart(data, height);
      case 'bar':
      default:
        return renderBarChart(data, height);
    }
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{title}</CardTitle>
          {onChartTypeChange && (
            <div className="flex items-center gap-2">
              <BarChart2 className="h-4 w-4 text-muted-foreground" />
              <div className="flex gap-1">
                <Button
                  variant={chartType === 'bar' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => onChartTypeChange('bar')}
                  className="h-7 px-2 text-xs"
                >
                  Çubuk
                </Button>
                <Button
                  variant={chartType === 'area' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => onChartTypeChange('area')}
                  className="h-7 px-2 text-xs"
                >
                  Alan
                </Button>
                <Button
                  variant={chartType === 'line' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => onChartTypeChange('line')}
                  className="h-7 px-2 text-xs"
                >
                  Çizgi
                </Button>
                <Button
                  variant={chartType === 'composed' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => onChartTypeChange('composed')}
                  className="h-7 px-2 text-xs"
                >
                  Karma
                </Button>
              </div>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          {renderChart()}
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
