export type PeriodType = 'hourly' | 'daily' | 'weekly' | 'monthly';
export type MetricType = '19l' | '5l' | 'total';

export interface AnalyticsDataPoint {
  timestamp: string;
  period_label: string;
  value_19l: number;
  value_5l: number;
  value_total: number;
  delta_19l: number;
  delta_5l: number;
  delta_total: number;
  reading_count: number;
  fault_count: number;
}

export interface RevenueAnalytics {
  device_id: number | null;
  device_name: string;
  period: PeriodType;
  start_date: string;
  end_date: string;
  data: AnalyticsDataPoint[];
  summary: {
    total_19l: number;
    total_5l: number;
    total_revenue: number;
    avg_per_period: number;
    max_period: {
      timestamp: string;
      value: number;
    };
    min_period: {
      timestamp: string;
      value: number;
    };
    trend_percentage: number;
  };
}

export interface DashboardOverview {
  total_devices: number;
  online_devices: number;
  offline_devices: number;
  pending_devices: number;
  today_revenue_19l: number;
  today_revenue_5l: number;
  today_revenue_total: number;
  month_revenue_19l: number;
  month_revenue_5l: number;
  month_revenue_total: number;
  last_updated: string;
}

export interface DashboardRealtime {
  devices: {
    id: number;
    name: string;
    status: DeviceStatus;
    last_reading: Reading | null;
    current_19l: number;
    current_5l: number;
    current_total: number;
  }[];
  timestamp: string;
}

export interface TopDevice {
  id: number;
  name: string;
  device_code: string;
  revenue_19l: number;
  revenue_5l: number;
  revenue_total: number;
  status: DeviceStatus;
}

export interface RecentOfflineDevice {
  id: number;
  name: string;
  device_code: string;
  last_seen_at: string;
  offline_duration_hours: number;
}

export interface DashboardAlert {
  id: number;
  type: 'offline' | 'fault' | 'spike';
  device_id: number;
  device_name: string;
  message: string;
  timestamp: string;
  is_resolved: boolean;
}

import { DeviceStatus } from './device';
import { Reading } from './reading';

export interface AnalyticsQueryParams {
  device_id?: number | 'all';
  period: PeriodType;
  start_date?: string;
  end_date?: string;
  metric?: MetricType;
}

export interface ComparisonData {
  device_id: number;
  device_name: string;
  period_1_total: number;
  period_2_total: number;
  change_percentage: number;
  change_amount: number;
}

export interface TrendData {
  timestamps: string[];
  values: number[];
  trend_line: number[];
  trend_direction: 'up' | 'down' | 'stable';
  trend_percentage: number;
}

export interface PeakHourData {
  hour: number;
  avg_revenue: number;
  max_revenue: number;
  reading_count: number;
}

export interface DowntimeData {
  device_id: number;
  device_name: string;
  total_downtime_hours: number;
  downtime_percentage: number;
  incidents: number;
  longest_downtime_hours: number;
}
