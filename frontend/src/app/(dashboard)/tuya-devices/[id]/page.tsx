'use client';

import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState, useCallback } from 'react';
import { ArrowLeft, Plug, Power, RefreshCw, Wifi, WifiOff, ToggleLeft, ToggleRight, Loader2, Clock, CheckCircle2, XCircle, Activity, ChevronLeft, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { api, endpoints } from '@/lib/api';
import type { TuyaDeviceDetailsResponse, TuyaDeviceControlResponse, TuyaDeviceControlHistoryResponse, TuyaDeviceStatusResponse } from '@/types/tuya';

export default function TuyaDeviceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const deviceId = Number(params.id);

  const [device, setDevice] = useState<TuyaDeviceDetailsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [controllingDevice, setControllingDevice] = useState(false);

  // Control history pagination
  const [historyPage, setHistoryPage] = useState(1);
  const [historyPageSize] = useState(20);
  const [history, setHistory] = useState<TuyaDeviceControlHistoryResponse | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Fetch device details
  const fetchDetails = useCallback(async () => {
    if (!deviceId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get<TuyaDeviceDetailsResponse>(endpoints.tuyaDeviceDetails(deviceId));
      setDevice(data);
    } catch (err) {
      console.error('Failed to fetch device details:', err);
      setError('Cihaz detayları yüklenirken bir hata oluştu');
    } finally {
      setIsLoading(false);
    }
  }, [deviceId]);

  // Fetch control history
  const fetchHistory = useCallback(async () => {
    if (!deviceId) return;
    setIsLoadingHistory(true);
    try {
      const data = await api.get<TuyaDeviceControlHistoryResponse>(
        endpoints.tuyaDeviceControlHistory(deviceId),
        { page: historyPage, page_size: historyPageSize }
      );
      setHistory(data);
    } catch (err) {
      console.error('Failed to fetch control history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  }, [deviceId, historyPage, historyPageSize]);

  // Control device
  const controlDevice = async (action: 'on' | 'off') => {
    setControllingDevice(true);
    try {
      const result = await api.post<TuyaDeviceControlResponse>(
        endpoints.tuyaDeviceControl(deviceId),
        { action: action === 'on' ? 'turn_on' : 'turn_off' }
      );
      if (result.success && device) {
        setDevice({
          ...device,
          power_state: result.power_state,
          last_control_at: new Date().toISOString(),
        });
      }
      // Refresh history after control
      await fetchHistory();
      await fetchDetails();
    } catch (err) {
      console.error('Failed to control device:', err);
      setError('Cihaz kontrol edilirken bir hata oluştu');
    } finally {
      setControllingDevice(false);
    }
  };

  // Toggle device
  const toggleDevice = async () => {
    setControllingDevice(true);
    try {
      const result = await api.post<TuyaDeviceControlResponse>(
        endpoints.tuyaDeviceToggle(deviceId)
      );
      if (result.success && device) {
        setDevice({
          ...device,
          power_state: result.power_state,
          last_control_at: new Date().toISOString(),
        });
      }
      await fetchHistory();
      await fetchDetails();
    } catch (err) {
      console.error('Failed to toggle device:', err);
      setError('Cihaz değiştirilirken bir hata oluştu');
    } finally {
      setControllingDevice(false);
    }
  };

  // Refresh device status from cloud
  const refreshStatus = async () => {
    try {
      const data = await api.get<TuyaDeviceStatusResponse>(endpoints.tuyaDeviceStatus(deviceId));
      if (device) {
        setDevice({
          ...device,
          is_online: data.is_online,
          power_state: data.power_state,
          last_seen_at: data.last_seen_at,
        });
      }
    } catch (err) {
      console.error('Failed to refresh device status:', err);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [fetchDetails]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('tr-TR');
  };

  const formatAction = (action: string) => {
    switch (action) {
      case 'turn_on': return 'Aç';
      case 'turn_off': return 'Kapat';
      case 'toggle': return 'Değiştir';
      default: return action;
    }
  };

  const totalPages = history ? Math.ceil(history.total / historyPageSize) : 0;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.push('/tuya-devices')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Geri
          </Button>
        </div>
        <Card>
          <CardContent className="p-8 text-center">
            <RefreshCw className="mx-auto h-8 w-8 animate-spin text-muted-foreground" />
            <p className="mt-2 text-muted-foreground">Cihaz detayları yükleniyor...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error && !device) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.push('/tuya-devices')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Geri
          </Button>
        </div>
        <Card className="border-destructive">
          <CardContent className="p-8 text-center">
            <XCircle className="mx-auto h-8 w-8 text-destructive" />
            <p className="mt-2 text-destructive">{error}</p>
            <Button variant="outline" className="mt-4" onClick={fetchDetails}>
              Tekrar Dene
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!device) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.push('/tuya-devices')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Geri
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
              <Plug className="h-8 w-8" />
              {device.name}
            </h1>
            <p className="text-muted-foreground mt-1">{device.device_id}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={refreshStatus}>
            <Wifi className="mr-2 h-4 w-4" />
            Durumu Yenile
          </Button>
          <Button variant="outline" size="sm" onClick={fetchDetails}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Yenile
          </Button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="p-4">
            <p className="text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Device Info & Control Section */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Device Status Card */}
        <Card className={`md:col-span-2 ${device.power_state ? 'border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20' : ''}`}>
          <CardHeader>
            <CardTitle>Cihaz Durumu</CardTitle>
            <CardDescription>Cihazın anlık durumu ve kontrol paneli</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Status Indicators */}
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div>
                  <p className="text-sm text-muted-foreground">Bağlantı</p>
                  <p className="text-lg font-semibold mt-1">
                    {device.is_online ? 'Online' : 'Offline'}
                  </p>
                </div>
                <Badge variant={device.is_online ? 'success' : 'destructive'} className="h-10 px-4">
                  {device.is_online ? (
                    <Wifi className="h-5 w-5" />
                  ) : (
                    <WifiOff className="h-5 w-5" />
                  )}
                </Badge>
              </div>
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div>
                  <p className="text-sm text-muted-foreground">Güç Durumu</p>
                  <p className="text-lg font-semibold mt-1">
                    {device.power_state ? 'Açık' : 'Kapalı'}
                  </p>
                </div>
                <Badge variant={device.power_state ? 'success' : 'secondary'} className="h-10 px-4">
                  {device.power_state ? (
                    <ToggleRight className="h-5 w-5" />
                  ) : (
                    <ToggleLeft className="h-5 w-5" />
                  )}
                </Badge>
              </div>
            </div>

            {/* Control Buttons */}
            <div className="flex gap-3">
              <Button
                size="lg"
                className="flex-1"
                onClick={() => controlDevice('on')}
                disabled={controllingDevice || device.power_state}
              >
                {controllingDevice ? (
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                ) : (
                  <Power className="mr-2 h-5 w-5" />
                )}
                Aç
              </Button>
              <Button
                variant="destructive"
                size="lg"
                className="flex-1"
                onClick={() => controlDevice('off')}
                disabled={controllingDevice || !device.power_state}
              >
                {controllingDevice ? (
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                ) : (
                  <Power className="mr-2 h-5 w-5" />
                )}
                Kapat
              </Button>
              <Button
                variant="outline"
                size="lg"
                onClick={toggleDevice}
                disabled={controllingDevice}
              >
                {controllingDevice ? (
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                ) : (
                  <RefreshCw className="mr-2 h-5 w-5" />
                )}
                Toggle
              </Button>
            </div>

            {/* Device Details */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Cihaz Tipi:</span>
                  <span className="font-medium">
                    {device.device_type === 'SMART_PLUG' ? 'Akıllı Priz' :
                     device.device_type === 'SMART_SWITCH' ? 'Akıllı Anahtar' :
                     device.device_type === 'SMART_BULB' ? 'Akıllı Ampul' :
                     device.device_type}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Durum:</span>
                  <Badge variant={device.is_enabled ? 'success' : 'secondary'}>
                    {device.is_enabled ? 'Aktif' : 'Devre Dışı'}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Son Görülme:</span>
                  <span>{formatDate(device.last_seen_at)}</span>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Son Kontrol:</span>
                  <span>{formatDate(device.last_control_at)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Eklenme:</span>
                  <span>{formatDate(device.created_at)}</span>
                </div>
                {device.ip_address && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">IP Adresi:</span>
                    <span className="font-mono">{device.ip_address}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Product Info */}
            {device.product_name && (
              <div className="rounded-lg border bg-muted/50 p-4">
                <p className="text-sm font-medium">{device.product_name}</p>
                {device.product_id && (
                  <p className="text-xs text-muted-foreground mt-1">Product ID: {device.product_id}</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Statistics Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Kontrol İstatistikleri
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-lg border p-3">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">Toplam Kontrol</span>
                </div>
                <span className="text-2xl font-bold">{device.total_controls}</span>
              </div>
              <div className="flex items-center justify-between rounded-lg border p-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                  <span className="text-sm">Başarılı</span>
                </div>
                <span className="text-2xl font-bold text-green-600">{device.successful_controls}</span>
              </div>
              <div className="flex items-center justify-between rounded-lg border p-3">
                <div className="flex items-center gap-2">
                  <XCircle className="h-4 w-4 text-red-500" />
                  <span className="text-sm">Başarısız</span>
                </div>
                <span className="text-2xl font-bold text-red-600">{device.failed_controls}</span>
              </div>
            </div>

            {/* Success Rate */}
            {device.total_controls > 0 && (
              <div className="rounded-lg border p-3">
                <p className="text-sm text-muted-foreground mb-2">Başarı Oranı</p>
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-3 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full bg-green-500 transition-all"
                      style={{
                        width: `${(device.successful_controls / device.total_controls) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="text-sm font-bold">
                    %{((device.successful_controls / device.total_controls) * 100).toFixed(0)}
                  </span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Controls from Details */}
      {device.recent_controls.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Son Kontrol İşlemleri</CardTitle>
            <CardDescription>En son yapılan 10 kontrol işlemi</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tarih</TableHead>
                  <TableHead>İşlem</TableHead>
                  <TableHead>Önceki Durum</TableHead>
                  <TableHead>Yeni Durum</TableHead>
                  <TableHead>Sonuç</TableHead>
                  <TableHead>Yapan</TableHead>
                  <TableHead>Hata</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {device.recent_controls.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="whitespace-nowrap text-sm">
                      {formatDate(log.performed_at)}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{formatAction(log.action)}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={log.previous_state ? 'success' : 'secondary'}>
                        {log.previous_state ? 'Açık' : 'Kapalı'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {log.new_state !== null ? (
                        <Badge variant={log.new_state ? 'success' : 'secondary'}>
                          {log.new_state ? 'Açık' : 'Kapalı'}
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {log.success ? (
                        <Badge variant="success">
                          <CheckCircle2 className="mr-1 h-3 w-3" />
                          Başarılı
                        </Badge>
                      ) : (
                        <Badge variant="destructive">
                          <XCircle className="mr-1 h-3 w-3" />
                          Başarısız
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-sm">
                      {log.performed_by || '-'}
                    </TableCell>
                    <TableCell className="text-sm text-destructive max-w-[200px] truncate">
                      {log.error_message || '-'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Full Control History with Pagination */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Kontrol Geçmişi</CardTitle>
              <CardDescription>
                {history ? `Toplam ${history.total} kayıt` : 'Yükleniyor...'}
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={fetchHistory} disabled={isLoadingHistory}>
              <RefreshCw className={`mr-2 h-4 w-4 ${isLoadingHistory ? 'animate-spin' : ''}`} />
              Yenile
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoadingHistory && !history ? (
            <div className="p-8 text-center">
              <RefreshCw className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
              <p className="mt-2 text-sm text-muted-foreground">Geçmiş yükleniyor...</p>
            </div>
          ) : history && history.items.length > 0 ? (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Tarih</TableHead>
                    <TableHead>İşlem</TableHead>
                    <TableHead>Önceki</TableHead>
                    <TableHead>Yeni</TableHead>
                    <TableHead>Sonuç</TableHead>
                    <TableHead>Yapan</TableHead>
                    <TableHead>Hata Mesajı</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {history.items.map((log) => (
                    <TableRow key={log.id}>
                      <TableCell className="whitespace-nowrap text-sm">
                        {formatDate(log.performed_at)}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{formatAction(log.action)}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={log.previous_state ? 'success' : 'secondary'}>
                          {log.previous_state ? 'Açık' : 'Kapalı'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {log.new_state !== null ? (
                          <Badge variant={log.new_state ? 'success' : 'secondary'}>
                            {log.new_state ? 'Açık' : 'Kapalı'}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {log.success ? (
                          <Badge variant="success">
                            <CheckCircle2 className="mr-1 h-3 w-3" />
                            Başarılı
                          </Badge>
                        ) : (
                          <Badge variant="destructive">
                            <XCircle className="mr-1 h-3 w-3" />
                            Başarısız
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-sm">
                        {log.performed_by || '-'}
                      </TableCell>
                      <TableCell className="text-sm text-destructive max-w-[200px] truncate">
                        {log.error_message || '-'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <p className="text-sm text-muted-foreground">
                    Sayfa {historyPage} / {totalPages} ({history.total} kayıt)
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setHistoryPage(prev => Math.max(1, prev - 1))}
                      disabled={historyPage <= 1}
                    >
                      <ChevronLeft className="mr-1 h-4 w-4" />
                      Önceki
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setHistoryPage(prev => Math.min(totalPages, prev + 1))}
                      disabled={historyPage >= totalPages}
                    >
                      Sonraki
                      <ChevronRight className="ml-1 h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="p-8 text-center text-muted-foreground">
              <Clock className="mx-auto h-8 w-8 mb-2" />
              <p>Henüz kontrol geçmişi bulunmuyor.</p>
              <p className="text-sm mt-1">Cihazı kontrol ettiğinizde burada görünecektir.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
