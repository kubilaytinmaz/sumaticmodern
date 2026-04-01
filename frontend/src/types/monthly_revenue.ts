/**
 * Monthly Revenue Types
 * Aylık ciro takip sistemi için TypeScript tipleri
 */

export interface MonthlyRevenueRecord {
  id?: number;
  device_id: number;
  year: number;
  month: number;
  month_start_date: string;
  month_end_date: string | null;
  closing_counter_19l: number | null;
  closing_counter_5l: number | null;
  total_revenue: number;
  is_closed: boolean;
}

export interface DeviceMonthCycle {
  cycle_start_date: string;
  cycle_end_date: string | null;
  start_counter_19l: number;
  start_counter_5l: number;
  end_counter_19l: number | null;
  end_counter_5l: number | null;
  total_revenue: number;
  year: number;
  month: number;
  is_closed: boolean;
}

export interface MonthlyRevenueSummary {
  year: number;
  month: number;
  total_revenue: number;
  total_19l: number;
  total_5l: number;
  device_count: number;
  closed_count: number;
}

export interface ActiveCycleRevenue {
  device_id: number;
  device_code: string;
  device_name: string;
  cycle_start_date: string;
  current_counter_19l: number;
  current_counter_5l: number;
  current_revenue: number;
  year: number;
  month: number;
}

export interface RevenueStatsOverview {
  current_month: {
    year: number;
    month: number;
    summary: MonthlyRevenueSummary;
    active_revenue: ActiveCycleRevenue[];
  };
  previous_month: {
    year: number;
    month: number;
    summary: MonthlyRevenueSummary;
  };
}

export interface MonthClosedAlert {
  type: 'month_closed';
  device_id: number;
  device_name: string;
  timestamp: string;
  message: string;
}
