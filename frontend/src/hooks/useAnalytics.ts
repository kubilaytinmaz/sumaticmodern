'use client';

import { useState, useEffect, useCallback } from 'react';
import { 
  AnalyticsDataPoint, 
  AnalyticsQueryParams, 
  RevenueAnalytics,
  DashboardOverview,
  TopDevice,
  RecentOfflineDevice,
  DashboardAlert
} from '@/types/analytics';
import { api, endpoints } from '@/lib/api';
import { useAuth } from './useAuth';

interface AnalyticsState {
  data: AnalyticsDataPoint[];
  analytics: RevenueAnalytics | null;
  overview: DashboardOverview | null;
  topDevices: TopDevice[];
  recentOffline: RecentOfflineDevice[];
  alerts: DashboardAlert[];
  isLoading: boolean;
  error: string | null;
}

interface UseAnalyticsReturn extends AnalyticsState {
  fetchAnalytics: (params: AnalyticsQueryParams) => Promise<void>;
  fetchOverview: () => Promise<void>;
  fetchTopDevices: (limit?: number) => Promise<void>;
  fetchRecentOffline: (limit?: number) => Promise<void>;
  fetchAlerts: () => Promise<void>;
  refresh: () => Promise<void>;
}

export function useAnalytics(): UseAnalyticsReturn {
  const { isAuthenticated } = useAuth();
  
  const [state, setState] = useState<AnalyticsState>({
    data: [],
    analytics: null,
    overview: null,
    topDevices: [],
    recentOffline: [],
    alerts: [],
    isLoading: false,
    error: null,
  });

  const fetchAnalytics = useCallback(async (params: AnalyticsQueryParams) => {
    if (!isAuthenticated) return;
    
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    
    try {
      const queryParams: Record<string, string | number | undefined> = {
        period: params.period,
      };
      
      if (params.device_id && params.device_id !== 'all') {
        queryParams.device_id = params.device_id as number;
      }
      if (params.start_date) {
        queryParams.start_date = params.start_date;
      }
      if (params.end_date) {
        queryParams.end_date = params.end_date;
      }
      if (params.metric) {
        queryParams.metric = params.metric;
      }

      const analytics = await api.get<RevenueAnalytics>(endpoints.analyticsRevenue, queryParams);
      
      setState((prev) => ({
        ...prev,
        analytics,
        data: analytics.data,
        isLoading: false,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Analiz verileri yüklenemedi';
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
    }
  }, [isAuthenticated]);

  const fetchOverview = useCallback(async () => {
    if (!isAuthenticated) return;
    
    try {
      const overview = await api.get<DashboardOverview>(endpoints.dashboardOverview);
      setState((prev) => ({ ...prev, overview }));
    } catch (error) {
      console.error('Failed to fetch overview:', error);
    }
  }, [isAuthenticated]);

  const fetchTopDevices = useCallback(async (limit: number = 5) => {
    if (!isAuthenticated) return;
    
    try {
      const topDevices = await api.get<TopDevice[]>(`${endpoints.dashboardOverview}/top-devices`, { limit });
      setState((prev) => ({ ...prev, topDevices }));
    } catch (error) {
      console.error('Failed to fetch top devices:', error);
    }
  }, [isAuthenticated]);

  const fetchRecentOffline = useCallback(async (limit: number = 5) => {
    if (!isAuthenticated) return;
    
    try {
      const recentOffline = await api.get<RecentOfflineDevice[]>(`${endpoints.dashboardOverview}/recent-offline`, { limit });
      setState((prev) => ({ ...prev, recentOffline }));
    } catch (error) {
      console.error('Failed to fetch recent offline:', error);
    }
  }, [isAuthenticated]);

  const fetchAlerts = useCallback(async () => {
    if (!isAuthenticated) return;
    
    try {
      const alerts = await api.get<DashboardAlert[]>(endpoints.dashboardAlerts);
      setState((prev) => ({ ...prev, alerts }));
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    }
  }, [isAuthenticated]);

  const refresh = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true }));
    await Promise.all([
      fetchOverview(),
      fetchTopDevices(),
      fetchRecentOffline(),
      fetchAlerts(),
    ]);
    setState((prev) => ({ ...prev, isLoading: false }));
  }, [fetchOverview, fetchTopDevices, fetchRecentOffline, fetchAlerts]);

  // Fetch overview on mount
  useEffect(() => {
    if (isAuthenticated) {
      fetchOverview();
    }
  }, [isAuthenticated, fetchOverview]);

  return {
    ...state,
    fetchAnalytics,
    fetchOverview,
    fetchTopDevices,
    fetchRecentOffline,
    fetchAlerts,
    refresh,
  };
}

// Hook for dashboard data
export function useDashboard() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [topDevices, setTopDevices] = useState<TopDevice[]>([]);
  const [recentOffline, setRecentOffline] = useState<RecentOfflineDevice[]>([]);
  const [alerts, setAlerts] = useState<DashboardAlert[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const [overviewData, topDevicesData, recentOfflineData, alertsData] = await Promise.all([
        api.get<DashboardOverview>(endpoints.dashboardOverview),
        api.get<TopDevice[]>(`${endpoints.dashboardOverview}/top-devices`, { limit: 5 }),
        api.get<RecentOfflineDevice[]>(`${endpoints.dashboardOverview}/recent-offline`, { limit: 5 }),
        api.get<DashboardAlert[]>(endpoints.dashboardAlerts),
      ]);
      
      setOverview(overviewData);
      setTopDevices(topDevicesData);
      setRecentOffline(recentOfflineData);
      setAlerts(alertsData);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Dashboard verileri yüklenemedi';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return {
    overview,
    topDevices,
    recentOffline,
    alerts,
    isLoading,
    error,
    refresh: fetchAll,
  };
}
