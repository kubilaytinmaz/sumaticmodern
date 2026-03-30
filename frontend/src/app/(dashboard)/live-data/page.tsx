'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Activity, Database, Wifi, WifiOff, RefreshCw, Clock } from 'lucide-react';

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

export default function LiveDataPage() {
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
      console.log('Live data WebSocket connected');
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
      console.log('Live data WebSocket disconnected');
    };

    ws.onerror = (error) => {
      console.error('Live data WebSocket error:', error);
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

  const selectedDeviceData = data?.devices.find(d => d.device_id === selectedDevice);

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Canlı Veri İzleme</h1>
          <p className="text-muted-foreground mt-1">
            Cihazların anlık durumunu ve veritabanına eklenen verileri gerçek zamanlı izleyin
          </p>
        </div>
        <div className="flex items-center gap-3">
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
            <p className="font-medium">❌ Hata</p>
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
                  <span className="text-xs font-medium text-muted-foreground uppercase">MQTT Bağlantı</span>
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
                  <span className="text-xs font-medium text-muted-foreground uppercase">Online Cihaz</span>
                  <div className="text-lg font-bold">
                    {data.devices.filter(d => d.is_online).length} / {data.devices.length}
                  </div>
                </div>
              </div>
            </Card>
            <Card className="p-4">
              <div className="flex items-center gap-3">
                <Database className="w-5 h-5 text-purple-500" />
                <div>
                  <span className="text-xs font-medium text-muted-foreground uppercase">Son Kayıt</span>
                  <div className="text-lg font-bold">{data.recent_insertions.length}</div>
                </div>
              </div>
            </Card>
            <Card className="p-4">
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-orange-500" />
                <div>
                  <span className="text-xs font-medium text-muted-foreground uppercase">Son Güncelleme</span>
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
                          <div>Modem: {device.modem_id} | Addr: {device.device_addr}</div>
                          <div>Son görülme: {formatTimeAgo(device.last_seen_at)}</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-muted-foreground mb-1">Cache Değerleri</div>
                        <div className="text-sm space-y-1">
                          {device.cache_data['Sayac 1'] !== undefined && (
                            <div>Sayaç 1: <span className="font-mono">{device.cache_data['Sayac 1']}</span></div>
                          )}
                          {device.cache_data['Sayac 2'] !== undefined && (
                            <div>Sayaç 2: <span className="font-mono">{device.cache_data['Sayac 2']}</span></div>
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
                    <h2 className="font-semibold">Cihaz Detayları: {selectedDeviceData.device_name}</h2>
                  </div>
                  <div className="p-4 space-y-4">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Cihaz Kodu:</span>
                        <div className="font-mono font-medium">{selectedDeviceData.device_code}</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Modem ID:</span>
                        <div className="font-mono font-medium">{selectedDeviceData.modem_id}</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Device Addr:</span>
                        <div className="font-mono font-medium">{selectedDeviceData.device_addr}</div>
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
                            <span className="font-mono">{formatTimestamp(selectedDeviceData.last_db_reading.timestamp)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Sayaç 1 (19L):</span>
                            <span className="font-mono font-medium">{selectedDeviceData.last_db_reading.counter_19l ?? '-'}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Sayaç 2 (5L):</span>
                            <span className="font-mono font-medium">{selectedDeviceData.last_db_reading.counter_5l ?? '-'}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Durum:</span>
                            <Badge variant={selectedDeviceData.last_db_reading.status === 'online' ? 'default' : 'secondary'}>
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
                      <div key={insertion.id} className="p-3 hover:bg-muted/40 transition-colors">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-medium text-sm">{insertion.device_code}</span>
                              <Badge
                                variant={insertion.status === 'online' ? 'default' : 'secondary'}
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
    </div>
  );
}
