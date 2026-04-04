'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Activity,
  Database,
  Wifi,
  WifiOff,
  RefreshCw,
  Clock,
  ChevronLeft,
  ChevronRight,
  Search,
  Table2,
  BarChart3,
  HardDrive,
  Filter,
  Download,
  Eye,
} from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

interface DeviceCacheData {
  [key: string]: number;
}

interface DeviceLiveData {
  device_id: number;
  device_code: string;
  device_name: string;
  modem_id: string;
  device_addr: number;
  is_online: boolean;
  last_seen_at: string | null;
  cache_data: DeviceCacheData;
  last_db_reading: {
    timestamp: string;
    counter_19l: number | null;
    counter_5l: number | null;
    status: string;
  } | null;
}

interface DatabaseInsertion {
  id: number;
  device_id: number;
  device_code: string;
  timestamp: string;
  counter_19l: number | null;
  counter_5l: number | null;
  status: string;
  created_at: string;
}

interface LiveDataResponse {
  devices: DeviceLiveData[];
  recent_insertions: DatabaseInsertion[];
  mqtt_status: {
    running: boolean;
    connected: boolean;
    known_modems: number;
    device_configs: number;
    cached_devices: number;
    broker_host: string;
    broker_port: number;
  };
  timestamp: string;
}

interface DbTableStats {
  table_name: string;
  total_count: number;
  recent_count_24h: number | null;
  oldest_record: string | null;
  newest_record: string | null;
}

interface DbBrowseResponse {
  table_name: string;
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  records: Record<string, any>[];
}

interface DbDevicesResponse {
  table_name: string;
  total_count: number;
  records: Record<string, any>[];
}

// ============================================================================
// TAB TYPES
// ============================================================================
type MainTab = 'live' | 'database';
type DbTab = 'overview' | 'readings' | 'devices' | 'hourly-status' | 'monthly-revenue';

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function LiveDataPage() {
  const [mainTab, setMainTab] = useState<MainTab>('live');

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Canlı Veri & Veritabanı</h1>
        <p className="text-muted-foreground mt-1">
          Cihazların anlık durumunu izleyin ve deploy veritabanını doğrudan görüntüleyin
        </p>
      </div>

      {/* Main Tab Selector */}
      <div className="flex gap-2 border-b border-border pb-2">
        <button
          onClick={() => setMainTab('live')}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
            mainTab === 'live'
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
          }`}
        >
          <Activity className="w-4 h-4" />
          Canlı İzleme
        </button>
        <button
          onClick={() => setMainTab('database')}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
            mainTab === 'database'
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
          }`}
        >
          <HardDrive className="w-4 h-4" />
          Veritabanı Tarayıcı
        </button>
      </div>

      {mainTab === 'live' ? <LiveMonitoringPanel /> : <DatabaseBrowserPanel />}
    </div>
  );
}

// ============================================================================
// LIVE MONITORING PANEL (existing functionality)
// ============================================================================

function LiveMonitoringPanel() {
  const [data, setData] = useState<LiveDataResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedDevice, setSelectedDevice] = useState<number | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const WS_URL = API_URL.replace('http', 'ws');

  const fetchData = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/live-data`);
      if (!response.ok) throw new Error('Failed to fetch live data');
      const result: LiveDataResponse = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load live data');
    } finally {
      setLoading(false);
    }
  }, [API_URL]);

  // WebSocket connection for real-time updates
  useEffect(() => {
    if (!autoRefresh) return;

    const ws = new WebSocket(`${WS_URL}/api/v1/ws/live-data`);

    ws.onopen = () => {
      setWsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        if (parsed.type === 'initial' || parsed.type === 'update') {
          setData(parsed.data);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
    };

    ws.onerror = () => {
      setWsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [WS_URL, autoRefresh]);

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh polling fallback (every 5 seconds)
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData, autoRefresh]);

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('tr-TR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const formatTimeAgo = (timestamp: string | null) => {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);

    if (diffSecs < 60) return `${diffSecs}s önce`;
    if (diffMins < 60) return `${diffMins}dk önce`;
    if (diffHours < 24) return `${diffHours}sa önce`;
    return date.toLocaleDateString('tr-TR');
  };

  const getStatusColor = (isOnline: boolean) => {
    return isOnline
      ? 'bg-green-500/10 text-green-500 border-green-500/20'
      : 'bg-red-500/10 text-red-500 border-red-500/20';
  };

  const getStatusIcon = (isOnline: boolean) => {
    return isOnline ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />;
  };

  const selectedDeviceData = data?.devices.find((d) => d.device_id === selectedDevice);

  return (
    <>
      {/* Controls */}
      <div className="flex items-center gap-3 justify-end">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-gray-400'}`} />
          <span className="text-sm text-muted-foreground">
            {wsConnected ? 'Canlı bağlı' : 'Çevrimdışı'}
          </span>
        </div>
        <Button
          variant={autoRefresh ? 'default' : 'outline'}
          size="sm"
          onClick={() => setAutoRefresh(!autoRefresh)}
        >
          {autoRefresh ? '⏸️ Duraklat' : '▶️ Başlat'}
        </Button>
        <Button variant="outline" size="sm" onClick={fetchData}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Yenile
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center p-12">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4" />
            <p className="text-muted-foreground">Veriler yükleniyor...</p>
          </div>
        </div>
      ) : error ? (
        <div className="flex items-center justify-center p-12">
          <div className="text-center text-red-500">
            <p className="font-medium">Hata</p>
            <p className="text-sm">{error}</p>
          </div>
        </div>
      ) : !data ? (
        <div className="flex items-center justify-center p-12">
          <div className="text-center text-muted-foreground">
            <p>Veri bulunmuyor</p>
          </div>
        </div>
      ) : (
        <>
          {/* MQTT Status Cards */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card className="p-4">
              <div className="flex items-center gap-3">
                <Activity className="w-5 h-5 text-blue-500" />
                <div>
                  <span className="text-xs font-medium text-muted-foreground uppercase">
                    MQTT Bağlantı
                  </span>
                  <div className="text-lg font-bold">
                    {data.mqtt_status.connected ? (
                      <span className="text-green-500">Bağlı</span>
                    ) : (
                      <span className="text-red-500">Bağlı Değil</span>
                    )}
                  </div>
                </div>
              </div>
            </Card>
            <Card className="p-4">
              <div className="flex items-center gap-3">
                <Wifi className="w-5 h-5 text-green-500" />
                <div>
                  <span className="text-xs font-medium text-muted-foreground uppercase">
                    Online Cihaz
                  </span>
                  <div className="text-lg font-bold">
                    {data.devices.filter((d) => d.is_online).length} / {data.devices.length}
                  </div>
                </div>
              </div>
            </Card>
            <Card className="p-4">
              <div className="flex items-center gap-3">
                <Database className="w-5 h-5 text-purple-500" />
                <div>
                  <span className="text-xs font-medium text-muted-foreground uppercase">
                    Son Kayıt
                  </span>
                  <div className="text-lg font-bold">{data.recent_insertions.length}</div>
                </div>
              </div>
            </Card>
            <Card className="p-4">
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-orange-500" />
                <div>
                  <span className="text-xs font-medium text-muted-foreground uppercase">
                    Son Güncelleme
                  </span>
                  <div className="text-sm font-medium">{formatTimeAgo(data.timestamp)}</div>
                </div>
              </div>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            {/* Devices List */}
            <Card className="overflow-hidden">
              <div className="bg-muted/30 px-4 py-3 border-b border-border/30">
                <h2 className="font-semibold">Cihazlar ({data.devices.length})</h2>
              </div>
              <div className="divide-y divide-border/20 max-h-[600px] overflow-y-auto">
                {data.devices.map((device) => (
                  <div
                    key={device.device_id}
                    onClick={() => setSelectedDevice(device.device_id)}
                    className={`p-4 cursor-pointer hover:bg-muted/40 transition-colors ${
                      selectedDevice === device.device_id ? 'bg-muted/60' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-medium truncate">{device.device_name}</h3>
                          <Badge className={getStatusColor(device.is_online)}>
                            {getStatusIcon(device.is_online)}
                            {device.is_online ? 'ONLINE' : 'OFFLINE'}
                          </Badge>
                        </div>
                        <div className="text-xs text-muted-foreground space-y-1">
                          <div>
                            Modem: {device.modem_id} | Addr: {device.device_addr}
                          </div>
                          <div>Son görülme: {formatTimeAgo(device.last_seen_at)}</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-muted-foreground mb-1">Cache Değerleri</div>
                        <div className="text-sm space-y-1">
                          {device.cache_data['Sayac 1'] !== undefined && (
                            <div>
                              Sayaç 1:{' '}
                              <span className="font-mono">{device.cache_data['Sayac 1']}</span>
                            </div>
                          )}
                          {device.cache_data['Sayac 2'] !== undefined && (
                            <div>
                              Sayaç 2:{' '}
                              <span className="font-mono">{device.cache_data['Sayac 2']}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            {/* Device Details & Recent Insertions */}
            <div className="space-y-6">
              {/* Selected Device Details */}
              {selectedDeviceData && (
                <Card className="overflow-hidden">
                  <div className="bg-muted/30 px-4 py-3 border-b border-border/30">
                    <h2 className="font-semibold">
                      Cihaz Detayları: {selectedDeviceData.device_name}
                    </h2>
                  </div>
                  <div className="p-4 space-y-4">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Cihaz Kodu:</span>
                        <div className="font-mono font-medium">
                          {selectedDeviceData.device_code}
                        </div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Modem ID:</span>
                        <div className="font-mono font-medium">{selectedDeviceData.modem_id}</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Device Addr:</span>
                        <div className="font-mono font-medium">
                          {selectedDeviceData.device_addr}
                        </div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Durum:</span>
                        <div>
                          <Badge className={getStatusColor(selectedDeviceData.is_online)}>
                            {getStatusIcon(selectedDeviceData.is_online)}
                            {selectedDeviceData.is_online ? 'ONLINE' : 'OFFLINE'}
                          </Badge>
                        </div>
                      </div>
                    </div>

                    {/* Cache Data */}
                    <div>
                      <h3 className="text-sm font-medium mb-2">Cache Verileri</h3>
                      <div className="bg-muted/50 rounded p-3">
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          {Object.entries(selectedDeviceData.cache_data).map(([key, value]) => (
                            <div key={key} className="flex justify-between">
                              <span className="text-muted-foreground">{key}:</span>
                              <span className="font-mono font-medium">{value}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Last DB Reading */}
                    {selectedDeviceData.last_db_reading && (
                      <div>
                        <h3 className="text-sm font-medium mb-2">Son DB Kaydı</h3>
                        <div className="bg-muted/50 rounded p-3 space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Zaman:</span>
                            <span className="font-mono">
                              {formatTimestamp(selectedDeviceData.last_db_reading.timestamp)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Sayaç 1 (19L):</span>
                            <span className="font-mono font-medium">
                              {selectedDeviceData.last_db_reading.counter_19l ?? '-'}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Sayaç 2 (5L):</span>
                            <span className="font-mono font-medium">
                              {selectedDeviceData.last_db_reading.counter_5l ?? '-'}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Durum:</span>
                            <Badge
                              variant={
                                selectedDeviceData.last_db_reading.status === 'online'
                                  ? 'default'
                                  : 'secondary'
                              }
                            >
                              {selectedDeviceData.last_db_reading.status.toUpperCase()}
                            </Badge>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </Card>
              )}

              {/* Recent Database Insertions */}
              <Card className="overflow-hidden">
                <div className="bg-muted/30 px-4 py-3 border-b border-border/30">
                  <h2 className="font-semibold flex items-center gap-2">
                    <Database className="w-4 h-4" />
                    Veritabanına Eklenen Son Kayıtlar
                  </h2>
                </div>
                <div className="divide-y divide-border/20 max-h-[400px] overflow-y-auto">
                  {data.recent_insertions.length === 0 ? (
                    <div className="p-8 text-center text-muted-foreground">
                      <Database className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p>Henüz kayıt eklenmemiş</p>
                    </div>
                  ) : (
                    data.recent_insertions.map((insertion) => (
                      <div
                        key={insertion.id}
                        className="p-3 hover:bg-muted/40 transition-colors"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-medium text-sm">
                                {insertion.device_code}
                              </span>
                              <Badge
                                variant={
                                  insertion.status === 'online' ? 'default' : 'secondary'
                                }
                                className="text-xs"
                              >
                                {insertion.status}
                              </Badge>
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {formatTimestamp(insertion.timestamp)}
                            </div>
                          </div>
                          <div className="text-right text-sm">
                            {insertion.counter_19l !== null && (
                              <div className="font-mono">19L: {insertion.counter_19l}</div>
                            )}
                            {insertion.counter_5l !== null && (
                              <div className="font-mono">5L: {insertion.counter_5l}</div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </Card>
            </div>
          </div>
        </>
      )}
    </>
  );
}

// ============================================================================
// DATABASE BROWSER PANEL (new functionality)
// ============================================================================

function DatabaseBrowserPanel() {
  const [dbTab, setDbTab] = useState<DbTab>('overview');

  const tabs: { id: DbTab; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: 'Genel Bakış', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'readings', label: 'Okumalar', icon: <Table2 className="w-4 h-4" /> },
    { id: 'devices', label: 'Cihazlar', icon: <Wifi className="w-4 h-4" /> },
    { id: 'hourly-status', label: 'Saatlik Durum', icon: <Clock className="w-4 h-4" /> },
    { id: 'monthly-revenue', label: 'Aylık Ciro', icon: <BarChart3 className="w-4 h-4" /> },
  ];

  return (
    <div className="space-y-4">
      {/* DB Sub-tabs */}
      <div className="flex flex-wrap gap-1 bg-muted/30 rounded-lg p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setDbTab(tab.id)}
            className={`flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
              dbTab === tab.id
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* DB Content */}
      {dbTab === 'overview' && <DbOverviewPanel />}
      {dbTab === 'readings' && <DbReadingsPanel />}
      {dbTab === 'devices' && <DbDevicesPanel />}
      {dbTab === 'hourly-status' && <DbHourlyStatusPanel />}
      {dbTab === 'monthly-revenue' && <DbMonthlyRevenuePanel />}
    </div>
  );
}

// ============================================================================
// DB OVERVIEW PANEL
// ============================================================================

function DbOverviewPanel() {
  const [stats, setStats] = useState<DbTableStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchStats = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/db/stats`);
      if (!response.ok) throw new Error('Failed to fetch database stats');
      const result = await response.json();
      setStats(result.stats);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Hata oluştu');
    } finally {
      setLoading(false);
    }
  }, [API_URL]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const formatNumber = (n: number) => n.toLocaleString('tr-TR');

  const formatDate = (d: string | null) => {
    if (!d) return '-';
    return new Date(d).toLocaleString('tr-TR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const tableLabels: Record<string, string> = {
    device_readings: 'Cihaz Okumaları',
    devices: 'Cihazlar',
    device_hourly_status: 'Saatlik Durum',
    device_status_snapshots: 'Durum Anlık Görüntüler',
    monthly_revenue_records: 'Aylık Ciro Kayıtları',
    device_month_cycles: 'Aylık Döngüler',
  };

  const tableColors: Record<string, string> = {
    device_readings: 'text-blue-500 bg-blue-500/10',
    devices: 'text-green-500 bg-green-500/10',
    device_hourly_status: 'text-purple-500 bg-purple-500/10',
    device_status_snapshots: 'text-orange-500 bg-orange-500/10',
    monthly_revenue_records: 'text-emerald-500 bg-emerald-500/10',
    device_month_cycles: 'text-cyan-500 bg-cyan-500/10',
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <Card className="p-8 text-center">
        <p className="text-red-500 font-medium">Hata: {error}</p>
        <Button variant="outline" size="sm" className="mt-4" onClick={fetchStats}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Tekrar Dene
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <HardDrive className="w-5 h-5" />
          Veritabanı Genel Bakış
        </h2>
        <Button variant="outline" size="sm" onClick={fetchStats}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Yenile
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {stats.map((stat) => (
          <Card key={stat.table_name} className="p-4">
            <div className="flex items-start gap-3">
              <div
                className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  tableColors[stat.table_name] || 'text-gray-500 bg-gray-500/10'
                }`}
              >
                <Database className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <h3 className="font-medium text-sm">
                  {tableLabels[stat.table_name] || stat.table_name}
                </h3>
                <p className="text-xs text-muted-foreground font-mono">{stat.table_name}</p>
                <div className="mt-2 space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Toplam Kayıt:</span>
                    <span className="font-bold font-mono">{formatNumber(stat.total_count)}</span>
                  </div>
                  {stat.recent_count_24h !== null && (
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Son 24 Saat:</span>
                      <span className="font-mono text-blue-500">
                        +{formatNumber(stat.recent_count_24h)}
                      </span>
                    </div>
                  )}
                  {stat.oldest_record && (
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">İlk Kayıt:</span>
                      <span className="font-mono">{formatDate(stat.oldest_record)}</span>
                    </div>
                  )}
                  {stat.newest_record && (
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">Son Kayıt:</span>
                      <span className="font-mono">{formatDate(stat.newest_record)}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// DB READINGS PANEL
// ============================================================================

function DbReadingsPanel() {
  const [data, setData] = useState<DbBrowseResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [filterDeviceId, setFilterDeviceId] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterStartDate, setFilterStartDate] = useState('');
  const [filterEndDate, setFilterEndDate] = useState('');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchReadings = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('page', page.toString());
      params.set('page_size', pageSize.toString());
      params.set('order', order);
      if (filterDeviceId) params.set('device_id', filterDeviceId);
      if (filterStatus) params.set('status', filterStatus);
      if (filterStartDate) params.set('start_date', new Date(filterStartDate).toISOString());
      if (filterEndDate) params.set('end_date', new Date(filterEndDate).toISOString());

      const response = await fetch(`${API_URL}/api/v1/db/readings?${params.toString()}`);
      if (!response.ok) throw new Error('Failed to fetch readings');
      const result: DbBrowseResponse = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Hata oluştu');
    } finally {
      setLoading(false);
    }
  }, [API_URL, page, pageSize, filterDeviceId, filterStatus, filterStartDate, filterEndDate, order]);

  useEffect(() => {
    fetchReadings();
  }, [fetchReadings]);

  const formatTimestamp = (ts: string) => {
    return new Date(ts).toLocaleString('tr-TR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const handleSearch = () => {
    setPage(1);
    fetchReadings();
  };

  const clearFilters = () => {
    setFilterDeviceId('');
    setFilterStatus('');
    setFilterStartDate('');
    setFilterEndDate('');
    setPage(1);
  };

  const exportCsv = () => {
    if (!data?.records.length) return;
    const headers = ['ID', 'Cihaz ID', 'Cihaz Kodu', 'Cihaz Adı', 'Zaman', 'Sayaç 19L', 'Sayaç 5L', 'Durum'];
    const rows = data.records.map((r) => [
      r.id,
      r.device_id,
      r.device_code,
      r.device_name,
      r.timestamp,
      r.counter_19l ?? '',
      r.counter_5l ?? '',
      r.status,
    ]);
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `readings_page${page}_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium">Filtreler</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Cihaz ID</label>
            <Input
              placeholder="Cihaz ID"
              value={filterDeviceId}
              onChange={(e) => setFilterDeviceId(e.target.value)}
              className="h-9"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Durum</label>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="">Tümü</option>
              <option value="online">Online</option>
              <option value="offline">Offline</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Başlangıç Tarihi</label>
            <Input
              type="datetime-local"
              value={filterStartDate}
              onChange={(e) => setFilterStartDate(e.target.value)}
              className="h-9"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Bitiş Tarihi</label>
            <Input
              type="datetime-local"
              value={filterEndDate}
              onChange={(e) => setFilterEndDate(e.target.value)}
              className="h-9"
            />
          </div>
          <div className="flex items-end gap-2">
            <Button size="sm" onClick={handleSearch} className="h-9">
              <Search className="w-4 h-4 mr-1" />
              Ara
            </Button>
            <Button size="sm" variant="outline" onClick={clearFilters} className="h-9">
              Temizle
            </Button>
          </div>
        </div>
      </Card>

      {/* Table Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">
            {data ? `Toplam ${data.total_count.toLocaleString('tr-TR')} kayıt` : ''}
          </span>
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setPage(1);
            }}
            className="h-8 rounded-md border border-input bg-background px-2 text-xs"
          >
            <option value={25}>25 / sayfa</option>
            <option value={50}>50 / sayfa</option>
            <option value={100}>100 / sayfa</option>
            <option value={200}>200 / sayfa</option>
          </select>
          <Button
            size="sm"
            variant="outline"
            className="h-8 text-xs"
            onClick={() => setOrder(order === 'desc' ? 'asc' : 'desc')}
          >
            {order === 'desc' ? '↓ Yeniden Eskiye' : '↑ Eskiden Yeniye'}
          </Button>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" className="h-8 text-xs" onClick={exportCsv}>
            <Download className="w-3 h-3 mr-1" />
            CSV
          </Button>
          <Button size="sm" variant="outline" className="h-8 text-xs" onClick={fetchReadings}>
            <RefreshCw className="w-3 h-3 mr-1" />
            Yenile
          </Button>
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center p-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : error ? (
        <Card className="p-8 text-center">
          <p className="text-red-500">{error}</p>
        </Card>
      ) : !data || data.records.length === 0 ? (
        <Card className="p-8 text-center text-muted-foreground">
          <Database className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>Kayıt bulunamadı</p>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/50 border-b border-border">
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">ID</th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">
                    Cihaz
                  </th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">
                    Zaman
                  </th>
                  <th className="text-right px-3 py-2 font-medium text-muted-foreground">
                    19L Sayaç
                  </th>
                  <th className="text-right px-3 py-2 font-medium text-muted-foreground">
                    5L Sayaç
                  </th>
                  <th className="text-center px-3 py-2 font-medium text-muted-foreground">
                    Durum
                  </th>
                  <th className="text-center px-3 py-2 font-medium text-muted-foreground">
                    Detay
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/30">
                {data.records.map((record) => (
                  <>
                    <tr
                      key={record.id}
                      className="hover:bg-muted/30 transition-colors"
                    >
                      <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
                        {record.id}
                      </td>
                      <td className="px-3 py-2">
                        <div className="font-medium text-xs">{record.device_code}</div>
                        <div className="text-xs text-muted-foreground">{record.device_name}</div>
                      </td>
                      <td className="px-3 py-2 font-mono text-xs">
                        {formatTimestamp(record.timestamp)}
                      </td>
                      <td className="px-3 py-2 text-right font-mono font-medium">
                        {record.counter_19l !== null ? (
                          record.counter_19l.toLocaleString('tr-TR')
                        ) : (
                          <span className="text-muted-foreground">NULL</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right font-mono font-medium">
                        {record.counter_5l !== null ? (
                          record.counter_5l.toLocaleString('tr-TR')
                        ) : (
                          <span className="text-muted-foreground">NULL</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-center">
                        <Badge
                          variant={record.status === 'online' ? 'default' : 'secondary'}
                          className="text-xs"
                        >
                          {record.status?.toUpperCase() || '-'}
                        </Badge>
                      </td>
                      <td className="px-3 py-2 text-center">
                        <button
                          onClick={() =>
                            setExpandedRow(expandedRow === record.id ? null : record.id)
                          }
                          className="p-1 hover:bg-muted rounded"
                        >
                          <Eye className="w-3.5 h-3.5 text-muted-foreground" />
                        </button>
                      </td>
                    </tr>
                    {expandedRow === record.id && (
                      <tr key={`${record.id}-detail`}>
                        <td colSpan={7} className="bg-muted/20 px-6 py-3">
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                            <div>
                              <span className="text-muted-foreground">Kayıt ID:</span>
                              <div className="font-mono font-medium">{record.id}</div>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Cihaz ID:</span>
                              <div className="font-mono font-medium">{record.device_id}</div>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Cihaz Kodu:</span>
                              <div className="font-mono font-medium">{record.device_code}</div>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Cihaz Adı:</span>
                              <div className="font-medium">{record.device_name}</div>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Zaman Damgası:</span>
                              <div className="font-mono font-medium">{record.timestamp}</div>
                            </div>
                            <div>
                              <span className="text-muted-foreground">19L Sayaç:</span>
                              <div className="font-mono font-medium">
                                {record.counter_19l ?? 'NULL'}
                              </div>
                            </div>
                            <div>
                              <span className="text-muted-foreground">5L Sayaç:</span>
                              <div className="font-mono font-medium">
                                {record.counter_5l ?? 'NULL'}
                              </div>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Durum:</span>
                              <div className="font-medium">{record.status}</div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data.total_pages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-border/30">
              <span className="text-xs text-muted-foreground">
                Sayfa {data.page} / {data.total_pages}
              </span>
              <div className="flex items-center gap-1">
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs"
                  disabled={page <= 1}
                  onClick={() => setPage(1)}
                >
                  İlk
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 w-7 p-0"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                >
                  <ChevronLeft className="w-3 h-3" />
                </Button>

                {/* Page numbers */}
                {(() => {
                  const pages: number[] = [];
                  const totalPages = data.total_pages;
                  const current = data.page;
                  const start = Math.max(1, current - 2);
                  const end = Math.min(totalPages, current + 2);
                  for (let i = start; i <= end; i++) pages.push(i);
                  return pages.map((p) => (
                    <Button
                      key={p}
                      size="sm"
                      variant={p === current ? 'default' : 'outline'}
                      className="h-7 w-7 p-0 text-xs"
                      onClick={() => setPage(p)}
                    >
                      {p}
                    </Button>
                  ));
                })()}

                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 w-7 p-0"
                  disabled={page >= data.total_pages}
                  onClick={() => setPage(page + 1)}
                >
                  <ChevronRight className="w-3 h-3" />
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs"
                  disabled={page >= data.total_pages}
                  onClick={() => setPage(data.total_pages)}
                >
                  Son
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

// ============================================================================
// DB DEVICES PANEL
// ============================================================================

function DbDevicesPanel() {
  const [data, setData] = useState<DbDevicesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchDevices = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/db/devices`);
      if (!response.ok) throw new Error('Failed to fetch devices');
      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Hata oluştu');
    } finally {
      setLoading(false);
    }
  }, [API_URL]);

  useEffect(() => {
    fetchDevices();
  }, [fetchDevices]);

  const formatTimestamp = (ts: string | null) => {
    if (!ts) return '-';
    return new Date(ts).toLocaleString('tr-TR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <Card className="p-8 text-center">
        <p className="text-red-500">{error}</p>
        <Button variant="outline" size="sm" className="mt-4" onClick={fetchDevices}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Tekrar Dene
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">
          Toplam {data?.total_count || 0} cihaz
        </span>
        <Button size="sm" variant="outline" onClick={fetchDevices}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Yenile
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data?.records.map((device) => (
          <Card key={device.id} className="p-4 space-y-3">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold text-sm">{device.name}</h3>
                <p className="text-xs font-mono text-muted-foreground">{device.device_code}</p>
              </div>
              <div className="flex gap-1">
                <Badge
                  variant={device.is_enabled ? 'default' : 'secondary'}
                  className="text-xs"
                >
                  {device.is_enabled ? 'Aktif' : 'Pasif'}
                </Badge>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-muted-foreground">ID:</span>
                <span className="font-mono ml-1">{device.id}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Modem:</span>
                <span className="font-mono ml-1">{device.modem_id}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Addr:</span>
                <span className="font-mono ml-1">{device.device_addr}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Konum:</span>
                <span className="ml-1">{device.location || '-'}</span>
              </div>
            </div>

            <div className="border-t border-border/30 pt-2 text-xs space-y-1">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Toplam Okuma:</span>
                <span className="font-mono font-medium">
                  {device.total_readings?.toLocaleString('tr-TR') || '0'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Son Görülme:</span>
                <span className="font-mono">{formatTimestamp(device.last_seen_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Oluşturulma:</span>
                <span className="font-mono">{formatTimestamp(device.created_at)}</span>
              </div>
            </div>

            {device.latest_reading && (
              <div className="bg-muted/40 rounded p-2 text-xs space-y-1">
                <div className="font-medium text-muted-foreground mb-1">Son Okuma</div>
                <div className="flex justify-between">
                  <span>Zaman:</span>
                  <span className="font-mono">{formatTimestamp(device.latest_reading.timestamp)}</span>
                </div>
                <div className="flex justify-between">
                  <span>19L:</span>
                  <span className="font-mono font-medium">
                    {device.latest_reading.counter_19l?.toLocaleString('tr-TR') ?? 'NULL'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>5L:</span>
                  <span className="font-mono font-medium">
                    {device.latest_reading.counter_5l?.toLocaleString('tr-TR') ?? 'NULL'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Durum:</span>
                  <Badge
                    variant={device.latest_reading.status === 'online' ? 'default' : 'secondary'}
                    className="text-xs h-5"
                  >
                    {device.latest_reading.status?.toUpperCase()}
                  </Badge>
                </div>
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// DB HOURLY STATUS PANEL
// ============================================================================

function DbHourlyStatusPanel() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [filterDeviceId, setFilterDeviceId] = useState('');

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('page', page.toString());
      params.set('page_size', '50');
      if (filterDeviceId) params.set('device_id', filterDeviceId);

      const response = await fetch(`${API_URL}/api/v1/db/hourly-status?${params.toString()}`);
      if (!response.ok) throw new Error('Failed to fetch hourly status');
      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Hata oluştu');
    } finally {
      setLoading(false);
    }
  }, [API_URL, page, filterDeviceId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const formatTimestamp = (ts: string) => {
    return new Date(ts).toLocaleString('tr-TR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case 'ONLINE':
        return <Badge className="bg-green-500/10 text-green-500 text-xs">ONLINE</Badge>;
      case 'OFFLINE':
        return <Badge className="bg-red-500/10 text-red-500 text-xs">OFFLINE</Badge>;
      case 'PARTIAL':
        return <Badge className="bg-yellow-500/10 text-yellow-500 text-xs">PARTIAL</Badge>;
      default:
        return <Badge variant="secondary" className="text-xs">{status}</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <Card className="p-8 text-center">
        <p className="text-red-500">{error}</p>
        <Button variant="outline" size="sm" className="mt-4" onClick={fetchData}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Tekrar Dene
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filter */}
      <Card className="p-4">
        <div className="flex items-center gap-3">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Cihaz ID</label>
            <Input
              placeholder="Cihaz ID"
              value={filterDeviceId}
              onChange={(e) => setFilterDeviceId(e.target.value)}
              className="h-9 w-40"
            />
          </div>
          <div className="flex items-end gap-2">
            <Button size="sm" onClick={() => { setPage(1); fetchData(); }} className="h-9">
              <Search className="w-4 h-4 mr-1" />
              Ara
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setFilterDeviceId('');
                setPage(1);
              }}
              className="h-9"
            >
              Temizle
            </Button>
          </div>
        </div>
      </Card>

      {/* Controls */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">
          Toplam {data?.total_count?.toLocaleString('tr-TR') || 0} kayıt
        </span>
        <Button size="sm" variant="outline" onClick={fetchData}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Yenile
        </Button>
      </div>

      {/* Table */}
      {data?.records?.length === 0 ? (
        <Card className="p-8 text-center text-muted-foreground">
          <p>Kayıt bulunamadı</p>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/50 border-b border-border">
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">ID</th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Cihaz</th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">
                    Saat Başlangıç
                  </th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">
                    Saat Bitiş
                  </th>
                  <th className="text-center px-3 py-2 font-medium text-muted-foreground">
                    Durum
                  </th>
                  <th className="text-right px-3 py-2 font-medium text-muted-foreground">
                    Online dk
                  </th>
                  <th className="text-right px-3 py-2 font-medium text-muted-foreground">
                    Offline dk
                  </th>
                  <th className="text-right px-3 py-2 font-medium text-muted-foreground">
                    Veri Noktası
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/30">
                {data?.records?.map((record: any) => (
                  <tr key={record.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
                      {record.id}
                    </td>
                    <td className="px-3 py-2 text-xs font-medium">{record.device_code}</td>
                    <td className="px-3 py-2 font-mono text-xs">
                      {formatTimestamp(record.hour_start)}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">
                      {formatTimestamp(record.hour_end)}
                    </td>
                    <td className="px-3 py-2 text-center">{getStatusBadge(record.status)}</td>
                    <td className="px-3 py-2 text-right font-mono text-green-500">
                      {record.online_minutes}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-red-500">
                      {record.offline_minutes}
                    </td>
                    <td className="px-3 py-2 text-right font-mono">{record.data_points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data?.total_pages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-border/30">
              <span className="text-xs text-muted-foreground">
                Sayfa {data.page} / {data.total_pages}
              </span>
              <div className="flex items-center gap-1">
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 w-7 p-0"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                >
                  <ChevronLeft className="w-3 h-3" />
                </Button>
                <span className="text-xs px-2">{page}</span>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 w-7 p-0"
                  disabled={page >= data.total_pages}
                  onClick={() => setPage(page + 1)}
                >
                  <ChevronRight className="w-3 h-3" />
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

// ============================================================================
// DB MONTHLY REVENUE PANEL
// ============================================================================

function DbMonthlyRevenuePanel() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/db/monthly-revenue`);
      if (!response.ok) throw new Error('Failed to fetch monthly revenue');
      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Hata oluştu');
    } finally {
      setLoading(false);
    }
  }, [API_URL]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const formatTimestamp = (ts: string | null) => {
    if (!ts) return '-';
    return new Date(ts).toLocaleString('tr-TR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const monthNames = [
    '',
    'Ocak',
    'Şubat',
    'Mart',
    'Nisan',
    'Mayıs',
    'Haziran',
    'Temmuz',
    'Ağustos',
    'Eylül',
    'Ekim',
    'Kasım',
    'Aralık',
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <Card className="p-8 text-center">
        <p className="text-red-500">{error}</p>
        <Button variant="outline" size="sm" className="mt-4" onClick={fetchData}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Tekrar Dene
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">
          Toplam {data?.total_count || 0} kayıt
        </span>
        <Button size="sm" variant="outline" onClick={fetchData}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Yenile
        </Button>
      </div>

      {data?.records?.length === 0 ? (
        <Card className="p-8 text-center text-muted-foreground">
          <p>Kayıt bulunamadı</p>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/50 border-b border-border">
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">ID</th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Cihaz</th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Dönem</th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">
                    Ay Başlangıç
                  </th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">
                    Ay Bitiş
                  </th>
                  <th className="text-right px-3 py-2 font-medium text-muted-foreground">
                    19L Kapanış
                  </th>
                  <th className="text-right px-3 py-2 font-medium text-muted-foreground">
                    5L Kapanış
                  </th>
                  <th className="text-right px-3 py-2 font-medium text-muted-foreground">
                    Toplam Ciro
                  </th>
                  <th className="text-center px-3 py-2 font-medium text-muted-foreground">
                    Kapalı
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/30">
                {data?.records?.map((record: any) => (
                  <tr key={record.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
                      {record.id}
                    </td>
                    <td className="px-3 py-2 text-xs font-medium">{record.device_code}</td>
                    <td className="px-3 py-2 text-xs">
                      {monthNames[record.month]} {record.year}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">
                      {formatTimestamp(record.month_start_date)}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">
                      {formatTimestamp(record.month_end_date)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono font-medium">
                      {record.closing_counter_19l?.toLocaleString('tr-TR') ?? '-'}
                    </td>
                    <td className="px-3 py-2 text-right font-mono font-medium">
                      {record.closing_counter_5l?.toLocaleString('tr-TR') ?? '-'}
                    </td>
                    <td className="px-3 py-2 text-right font-mono font-bold text-emerald-500">
                      {record.total_revenue?.toLocaleString('tr-TR') || '0'}
                    </td>
                    <td className="px-3 py-2 text-center">
                      <Badge
                        variant={record.is_closed ? 'default' : 'secondary'}
                        className="text-xs"
                      >
                        {record.is_closed ? 'Evet' : 'Hayır'}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
