'use client';

import { TrendingUp, TrendingDown, Minus, Calendar } from 'lucide-react';
import { formatMoney } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface ChartMetricsHeaderProps {
  type: 'revenue' | 'delta';
  metrics: {
    totalRevenue?: number;
    revenue19l?: number;
    revenue5l?: number;
    lastPeriod?: number;
    change?: number;
    min?: number;
    max?: number;
    avg?: number;
    // New metrics from backend
    totalPeriodRevenue?: number;
    avgRevenue?: number;
    activeDeviceCount?: number;
    totalDeviceCount?: number;
    offlineHours?: number;
  };
  periodOffset?: number;
  onPeriodOffsetChange?: (offset: number) => void;
  showPeriodToggle?: boolean;
}

export function ChartMetricsHeader({
  type,
  metrics,
  periodOffset = 0,
  onPeriodOffsetChange,
  showPeriodToggle = false
}: ChartMetricsHeaderProps) {
  if (type === 'revenue') {
    return (
      <div className="mb-4 grid grid-cols-3 gap-3">
        {/* Toplam Ciro */}
        <div className="p-4 rounded-lg bg-gradient-to-r from-primary/10 to-primary/5 border border-primary/20 relative">
          {showPeriodToggle && onPeriodOffsetChange && (
            <div className="absolute top-2 right-2 flex items-center gap-1">
              <Button
                variant={periodOffset === 0 ? "default" : "ghost"}
                size="sm"
                onClick={() => onPeriodOffsetChange(0)}
                className="h-6 px-2 text-xs"
              >
                Bu Ay
              </Button>
              <Button
                variant={periodOffset === 1 ? "default" : "ghost"}
                size="sm"
                onClick={() => onPeriodOffsetChange(1)}
                className="h-6 px-2 text-xs"
              >
                Geçen Ay
              </Button>
            </div>
          )}
          <div className="text-center">
            <div className="text-2xl font-bold text-primary">
              {formatMoney(metrics.totalPeriodRevenue ?? metrics.totalRevenue ?? 0)}
            </div>
            <div className="text-xs text-muted-foreground mt-1 flex items-center justify-center gap-1">
              <Calendar className="h-3 w-3" />
              {periodOffset === 1 ? 'Geçen Ay Ciro' : 'Bu Ay Ciro'}
            </div>
          </div>
        </div>
        
        {/* Sayaç 1 (19L) Ciro */}
        <div className="p-4 rounded-lg bg-gradient-to-r from-blue-500/10 to-blue-500/5 border border-blue-500/20">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {formatMoney(metrics.revenue19l || 0)}
            </div>
            <div className="text-xs text-muted-foreground mt-1">Sayaç 1 (19L)</div>
          </div>
        </div>
        
        {/* Sayaç 2 (5L) Ciro */}
        <div className="p-4 rounded-lg bg-gradient-to-r from-green-500/10 to-green-500/5 border border-green-500/20">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {formatMoney(metrics.revenue5l || 0)}
            </div>
            <div className="text-xs text-muted-foreground mt-1">Sayaç 2 (5L)</div>
          </div>
        </div>
      </div>
    );
  }

  // Delta type - 5 column metrics grid
  const lastPeriod = metrics.lastPeriod || 0;
  const change = metrics.change || 0;
  const min = metrics.min || 0;
  const max = metrics.max || 0;
  const avg = metrics.avg || 0;

  const changeIcon = change > 0 ? (
    <TrendingUp className="h-3 w-3 text-green-600" />
  ) : change < 0 ? (
    <TrendingDown className="h-3 w-3 text-red-600" />
  ) : (
    <Minus className="h-3 w-3 text-muted-foreground" />
  );

  const changeColor = change > 0 ? 'text-green-600' : change < 0 ? 'text-red-600' : 'text-muted-foreground';

  return (
    <div className="mb-4 grid grid-cols-5 gap-2">
      {/* Son Periyot */}
      <div className="p-3 rounded-md bg-primary/5 border border-primary/10">
        <div className="text-xs text-muted-foreground mb-1">Son Periyot</div>
        <div className="text-lg font-bold text-primary">{formatMoney(lastPeriod)}</div>
      </div>

      {/* Değişim */}
      <div className="p-3 rounded-md bg-background border border-border">
        <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
          Değişim {changeIcon}
        </div>
        <div className={`text-lg font-bold ${changeColor}`}>
          {change > 0 ? '+' : ''}{formatMoney(change)}
        </div>
      </div>

      {/* Min */}
      <div className="p-3 rounded-md bg-background border border-border">
        <div className="text-xs text-muted-foreground mb-1">Min</div>
        <div className="text-lg font-bold text-muted-foreground">{formatMoney(min)}</div>
      </div>

      {/* Max */}
      <div className="p-3 rounded-md bg-background border border-border">
        <div className="text-xs text-muted-foreground mb-1">Max</div>
        <div className="text-lg font-bold text-muted-foreground">{formatMoney(max)}</div>
      </div>

      {/* Ortalama Kazanç (merged with Ortalama Artış) */}
      <div className="p-3 rounded-md bg-accent/5 border border-accent/10">
        <div className="text-xs text-muted-foreground mb-1">Ort. Kazanç</div>
        <div className="text-lg font-bold text-accent-foreground">{formatMoney(metrics.avgRevenue ?? avg)}</div>
      </div>
    </div>
  );
}
