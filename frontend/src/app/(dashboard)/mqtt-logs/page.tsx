'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { ChevronDown, ChevronUp, Download } from 'lucide-react';

interface MQTTLog {
  timestamp: string;
  level: string;
  message: string;
  modem_id?: string;
  device_code?: string;
  data?: Record<string, any>;
}

interface ExpandedLog {
  [key: number]: boolean;
}

const LEVEL_COLORS: Record<string, string> = {
  info: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  warning: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
  error: 'bg-red-500/10 text-red-500 border-red-500/20',
  debug: 'bg-gray-500/10 text-gray-500 border-gray-500/20',
};

const LEVEL_ICONS: Record<string, string> = {
  info: 'ℹ️',
  warning: '⚠️',
  error: '❌',
  debug: '🔍',
};

const TIME_RANGE_FILTERS = [
  { value: 'all', label: 'Tümü' },
  { value: '5min', label: 'Son 5 dakika' },
  { value: '15min', label: 'Son 15 dakika' },
  { value: '1hour', label: 'Son 1 saat' },
];

export default function MQTTLogsPage() {
  const [logs, setLogs] = useState<MQTTLog[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<MQTTLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [levelFilter, setLevelFilter] = useState<string>('all');
  const [timeRangeFilter, setTimeRangeFilter] = useState<string>('all');
  const [textSearch, setTextSearch] = useState<string>('');
  const [modemFilter, setModemFilter] = useState<string>('all');
  const [deviceFilter, setDeviceFilter] = useState<string>('all');
  const [liveMode, setLiveMode] = useState<boolean>(true);
  const [limit, setLimit] = useState<number>(1000);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [expandedLogs, setExpandedLogs] = useState<ExpandedLog>({});
  const [stats, setStats] = useState({
    total: 0,
    errors: 0,
    warnings: 0,
    info: 0,
    debug: 0,
  });

  const logsEndRef = useRef<HTMLDivElement>(null);
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const WS_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace('http', 'ws');

  // Get unique modems and devices
  const uniqueModems = Array.from(new Set(logs.map(log => log.modem_id).filter(Boolean))) as string[];
  const uniqueDevices = Array.from(new Set(logs.map(log => log.device_code).filter(Boolean))) as string[];

  // Auto-scroll to bottom when live mode is enabled
  useEffect(() => {
    if (liveMode) {
      logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [filteredLogs, liveMode]);

  // Calculate stats
  useEffect(() => {
    const newStats = {
      total: logs.length,
      errors: logs.filter(l => l.level === 'error').length,
      warnings: logs.filter(l => l.level === 'warning').length,
      info: logs.filter(l => l.level === 'info').length,
      debug: logs.filter(l => l.level === 'debug').length,
    };
    setStats(newStats);
  }, [logs]);

  // Filter logs based on all criteria
  useEffect(() => {
    let filtered = [...logs];

    // Level filter
    if (levelFilter !== 'all') {
      filtered = filtered.filter(log => log.level === levelFilter);
    }

    // Text search
    if (textSearch.trim()) {
      const searchLower = textSearch.toLowerCase();
      filtered = filtered.filter(
        log =>
          log.message.toLowerCase().includes(searchLower) ||
          log.modem_id?.toLowerCase().includes(searchLower) ||
          log.device_code?.toLowerCase().includes(searchLower)
      );
    }

    // Modem filter
    if (modemFilter !== 'all') {
      filtered = filtered.filter(log => log.modem_id === modemFilter);
    }

    // Device filter
    if (deviceFilter !== 'all') {
      filtered = filtered.filter(log => log.device_code === deviceFilter);
    }

    // Time range filter
    if (timeRangeFilter !== 'all') {
      const now = new Date();
      let cutoffTime = new Date();

      switch (timeRangeFilter) {
        case '5min':
          cutoffTime.setMinutes(cutoffTime.getMinutes() - 5);
          break;
        case '15min':
          cutoffTime.setMinutes(cutoffTime.getMinutes() - 15);
          break;
        case '1hour':
          cutoffTime.setHours(cutoffTime.getHours() - 1);
          break;
      }

      filtered = filtered.filter(log => new Date(log.timestamp) >= cutoffTime);
    }

    setFilteredLogs([...filtered].reverse());
  }, [logs, levelFilter, textSearch, modemFilter, deviceFilter, timeRangeFilter]);

  const fetchLogs = useCallback(async () => {
    try {
      const params = new URLSearchParams({
        limit: limit.toString(),
      });

      const response = await fetch(`${API_URL}/api/v1/mqtt-logs?${params}`);
      if (!response.ok) throw new Error('Failed to fetch logs');

      const data: MQTTLog[] = await response.json();
      setLogs(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load logs');
    } finally {
      setLoading(false);
    }
  }, [API_URL, limit]);

  // WebSocket connection for real-time updates
  useEffect(() => {
    if (!autoRefresh) return;

    const ws = new WebSocket(`${WS_URL}/api/v1/ws/mqtt-logs`);

    ws.onopen = () => {
      setWsConnected(true);
      console.log('MQTT logs WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);

        if (parsed.type === 'initial') {
          setLogs(parsed.logs || []);
        } else if (parsed.type === 'new_logs') {
          setLogs((prev) => [...parsed.logs, ...prev].slice(0, limit));
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
      console.log('MQTT logs WebSocket disconnected');
    };

    ws.onerror = (error) => {
      console.error('MQTT logs WebSocket error:', error);
      setWsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [WS_URL, autoRefresh, limit]);

  // Initial fetch
  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  // Auto-refresh polling fallback (every 10 seconds)
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchLogs();
    }, 10000);

    return () => clearInterval(interval);
  }, [fetchLogs, autoRefresh]);

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

  const toggleLogExpand = (index: number) => {
    setExpandedLogs((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  const exportLogs = (format: 'json' | 'csv') => {
    let content: string;
    let filename: string;
    let mimeType: string;

    if (format === 'json') {
      content = JSON.stringify(filteredLogs, null, 2);
      filename = `mqtt-logs-${new Date().toISOString()}.json`;
      mimeType = 'application/json';
    } else {
      // CSV format
      const headers = ['Zaman', 'Seviye', 'Mesaj', 'Modem ID', 'Cihaz', 'Veri'];
      const rows = filteredLogs.map(log => [
        formatTimestamp(log.timestamp),
        log.level,
        log.message,
        log.modem_id || '-',
        log.device_code || '-',
        log.data ? JSON.stringify(log.data) : '-',
      ]);

      content = [headers, ...rows]
        .map(row => row.map(cell => `"${cell}"`).join(','))
        .join('\n');

      filename = `mqtt-logs-${new Date().toISOString()}.csv`;
      mimeType = 'text/csv';
    }

    const blob = new Blob([content], { type: mimeType });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">MQTT Logları</h1>
          <p className="text-muted-foreground mt-1">
            Canlı MQTT mesajlaşma ve veri akışı loglarını izleyin
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
          <Button variant="outline" size="sm" onClick={fetchLogs}>
            🔄 Yenile
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card className="p-4">
          <div className="flex flex-col">
            <span className="text-xs font-medium text-muted-foreground uppercase">Toplam Log</span>
            <span className="text-2xl font-bold mt-2">{stats.total}</span>
          </div>
        </Card>
        <Card className="p-4 border-red-500/20 bg-red-500/5">
          <div className="flex flex-col">
            <span className="text-xs font-medium text-red-600 uppercase">Hata</span>
            <span className="text-2xl font-bold text-red-600 mt-2">{stats.errors}</span>
          </div>
        </Card>
        <Card className="p-4 border-yellow-500/20 bg-yellow-500/5">
          <div className="flex flex-col">
            <span className="text-xs font-medium text-yellow-600 uppercase">Uyarı</span>
            <span className="text-2xl font-bold text-yellow-600 mt-2">{stats.warnings}</span>
          </div>
        </Card>
        <Card className="p-4 border-blue-500/20 bg-blue-500/5">
          <div className="flex flex-col">
            <span className="text-xs font-medium text-blue-600 uppercase">Bilgi</span>
            <span className="text-2xl font-bold text-blue-600 mt-2">{stats.info}</span>
          </div>
        </Card>
        <Card className="p-4 border-gray-500/20 bg-gray-500/5">
          <div className="flex flex-col">
            <span className="text-xs font-medium text-gray-600 uppercase">Debug</span>
            <span className="text-2xl font-bold text-gray-600 mt-2">{stats.debug}</span>
          </div>
        </Card>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="space-y-4">
          {/* Text Search */}
          <div>
            <label className="text-sm font-medium mb-2 block">Metin Arama</label>
            <Input
              placeholder="Mesaj, Modem ID veya Cihaz kodunda ara..."
              value={textSearch}
              onChange={(e) => setTextSearch(e.target.value)}
              className="w-full"
            />
          </div>

          {/* Filter Row */}
          <div className="grid gap-4 md:grid-cols-5">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">Seviye</label>
              <Select value={levelFilter} onValueChange={setLevelFilter}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tümü</SelectItem>
                  <SelectItem value="info">ℹ️ Info</SelectItem>
                  <SelectItem value="warning">⚠️ Warning</SelectItem>
                  <SelectItem value="error">❌ Error</SelectItem>
                  <SelectItem value="debug">🔍 Debug</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">Zaman Aralığı</label>
              <Select value={timeRangeFilter} onValueChange={setTimeRangeFilter}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TIME_RANGE_FILTERS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">Modem ID</label>
              <Select value={modemFilter} onValueChange={setModemFilter}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tümü ({uniqueModems.length})</SelectItem>
                  {uniqueModems.map((modem) => (
                    <SelectItem key={modem} value={modem}>
                      {modem}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">Cihaz</label>
              <Select value={deviceFilter} onValueChange={setDeviceFilter}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tümü ({uniqueDevices.length})</SelectItem>
                  {uniqueDevices.map((device) => (
                    <SelectItem key={device} value={device}>
                      {device}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">Limit</label>
              <Select value={limit.toString()} onValueChange={(v) => setLimit(Number(v))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="100">100</SelectItem>
                  <SelectItem value="200">200</SelectItem>
                  <SelectItem value="500">500</SelectItem>
                  <SelectItem value="1000">1000</SelectItem>
                  <SelectItem value="2000">2000</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Control Row */}
          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-2">
              <Button
                variant={liveMode ? 'default' : 'outline'}
                size="sm"
                onClick={() => setLiveMode(!liveMode)}
              >
                {liveMode ? '📍 Canlı Mod Aktif' : '📍 Canlı Mod Kapalı'}
              </Button>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => exportLogs('json')}
              >
                <Download className="w-4 h-4 mr-2" />
                JSON İndir
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => exportLogs('csv')}
              >
                <Download className="w-4 h-4 mr-2" />
                CSV İndir
              </Button>
            </div>
          </div>

          <div className="text-sm text-muted-foreground">
            Gösterilen: {filteredLogs.length} / Toplam: {logs.length}
          </div>
        </div>
      </Card>

      {/* Terminal-style Log Viewer */}
      <Card className="overflow-hidden border border-border/50">
        <div className="bg-muted/30 px-4 py-3 border-b border-border/30">
          <div className="text-xs font-mono text-muted-foreground">
            $ mqtt-logs --live --follow
          </div>
        </div>

        <div className="bg-background/50">
          {loading ? (
            <div className="flex items-center justify-center p-12">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4" />
                <p className="text-muted-foreground">Loglar yükleniyor...</p>
              </div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center p-12">
              <div className="text-center text-red-500">
                <p className="font-medium">❌ Hata</p>
                <p className="text-sm">{error}</p>
              </div>
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="flex items-center justify-center p-12">
              <div className="text-center text-muted-foreground">
                <p className="text-4xl mb-4">📭</p>
                <p>Henüz log kaydı bulunmuyor</p>
              </div>
            </div>
          ) : (
            <div className="max-h-[800px] overflow-y-auto font-mono text-sm">
              {filteredLogs.map((log, index) => (
                <div
                  key={`${log.timestamp}-${index}`}
                  className="border-b border-border/20 hover:bg-muted/40 transition-colors"
                >
                  {/* Main Log Row */}
                  <div
                    onClick={() => log.data && toggleLogExpand(index)}
                    className={`p-3 flex items-start gap-3 ${log.data ? 'cursor-pointer' : ''}`}
                  >
                    {/* Expand/Collapse Icon */}
                    <div className="w-5 flex-shrink-0">
                      {log.data && (
                        <button className="text-muted-foreground hover:text-foreground">
                          {expandedLogs[index] ? (
                            <ChevronDown className="w-4 h-4" />
                          ) : (
                            <ChevronUp className="w-4 h-4" />
                          )}
                        </button>
                      )}
                    </div>

                    {/* Timestamp */}
                    <div className="text-xs text-muted-foreground flex-shrink-0 w-48">
                      [{formatTimestamp(log.timestamp)}]
                    </div>

                    {/* Level Badge */}
                    <Badge className={`${LEVEL_COLORS[log.level] || LEVEL_COLORS.info} flex-shrink-0`}>
                      {LEVEL_ICONS[log.level] || '📝'} {log.level.toUpperCase()}
                    </Badge>

                    {/* Message and Details */}
                    <div className="flex-1 min-w-0">
                      <div className="break-words">{log.message}</div>
                      <div className="text-xs text-muted-foreground mt-1 space-x-4">
                        {log.modem_id && <span>Modem: {log.modem_id}</span>}
                        {log.device_code && <span>Cihaz: {log.device_code}</span>}
                      </div>
                    </div>
                  </div>

                  {/* Expanded JSON Data */}
                  {log.data && expandedLogs[index] && (
                    <div className="px-3 py-2 bg-muted/50 border-t border-border/20">
                      <pre className="text-xs bg-background rounded p-3 overflow-x-auto max-w-full">
                        {JSON.stringify(log.data, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
