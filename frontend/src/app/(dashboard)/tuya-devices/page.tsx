'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Plug, Power, RefreshCw, Plus, Wifi, WifiOff, Trash2, ToggleLeft, ToggleRight, Loader2, Settings, Cloud, CloudOff, CheckCircle2, AlertCircle, ExternalLink, RotateCcw } from 'lucide-react';
import { api, endpoints } from '@/lib/api';
import type { TuyaDevice, TuyaDeviceListResponse, TuyaDeviceControlResponse, TuyaDeviceStatusResponse, TuyaDeviceCreate, TuyaDiscoveryResponse, TuyaDiscoveredDevice, TuyaConfig, TuyaConfigResponse } from '@/types/tuya';

export default function TuyaDevicesPage() {
  const router = useRouter();
  const [devices, setDevices] = useState<TuyaDevice[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [controllingDevice, setControllingDevice] = useState<number | null>(null);
  const [restartingDevice, setRestartingDevice] = useState<number | null>(null);
  
  // Add Device Dialog
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [newDevice, setNewDevice] = useState<Partial<TuyaDeviceCreate>>({
    device_id: '',
    name: '',
    device_type: 'SMART_PLUG',
  });

  // Discover Dialog
  const [isDiscoverDialogOpen, setIsDiscoverDialogOpen] = useState(false);
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [discoveredDevices, setDiscoveredDevices] = useState<TuyaDiscoveredDevice[]>([]);

  // Config Dialog
  const [isConfigDialogOpen, setIsConfigDialogOpen] = useState(false);
  const [isLoadingConfig, setIsLoadingConfig] = useState(false);
  const [isSavingConfig, setIsSavingConfig] = useState(false);
  const [tuyaConfig, setTuyaConfig] = useState<TuyaConfigResponse | null>(null);
  const [configForm, setConfigForm] = useState<TuyaConfig>({
    access_id: '',
    access_secret: '',
    api_region: 'eu',
  });

  // Fetch Tuya devices
  const fetchDevices = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get<TuyaDeviceListResponse>(endpoints.tuyaDevices);
      setDevices(data.items);
    } catch (err) {
      console.error('Failed to fetch Tuya devices:', err);
      setError('Cihazlar yüklenirken bir hata oluştu');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Discover devices from Tuya Cloud
  const discoverDevices = async () => {
    setIsDiscovering(true);
    try {
      const data = await api.get<TuyaDiscoveryResponse>(endpoints.tuyaDiscover);
      setDiscoveredDevices(data.devices);
      setIsDiscoverDialogOpen(true);
    } catch (err) {
      console.error('Failed to discover devices:', err);
      setError('Cihazlar keşfedilirken bir hata oluştu. Tuya API bilgilerinizi kontrol edin.');
    } finally {
      setIsDiscovering(false);
    }
  };

  // Add discovered device
  const addDiscoveredDevice = async (device: TuyaDiscoveredDevice) => {
    try {
      const deviceData: TuyaDeviceCreate = {
        device_id: device.device_id,
        name: device.name,
        device_type: device.device_type || 'SMART_PLUG',
        local_key: device.local_key,
        ip_address: device.ip,
        product_id: device.product_id,
        product_name: device.product_name,
        is_enabled: true,
      };

      await api.post(endpoints.tuyaDevices, deviceData);
      setDiscoveredDevices(prev => prev.filter(d => d.device_id !== device.device_id));
      await fetchDevices();
    } catch (err: any) {
      console.error('Failed to add device:', err);
      if (err.status === 409) {
        setError('Bu cihaz zaten eklenmiş');
      } else {
        setError('Cihaz eklenirken bir hata oluştu');
      }
    }
  };

  // Add device manually
  const addDevice = async () => {
    if (!newDevice.device_id || !newDevice.name) {
      setError('Device ID ve İsim alanları zorunludur');
      return;
    }

    setIsAdding(true);
    setError(null);
    try {
      const deviceData: TuyaDeviceCreate = {
        device_id: newDevice.device_id,
        name: newDevice.name,
        device_type: newDevice.device_type || 'SMART_PLUG',
        local_key: newDevice.local_key,
        ip_address: newDevice.ip_address,
        product_id: newDevice.product_id,
        product_name: newDevice.product_name,
        is_enabled: true,
      };

      await api.post(endpoints.tuyaDevices, deviceData);
      setIsAddDialogOpen(false);
      setNewDevice({
        device_id: '',
        name: '',
        device_type: 'SMART_PLUG',
      });
      await fetchDevices();
    } catch (err: any) {
      console.error('Failed to add device:', err);
      if (err.status === 409) {
        setError('Bu cihaz ID zaten mevcut');
      } else {
        setError('Cihaz eklenirken bir hata oluştu');
      }
    } finally {
      setIsAdding(false);
    }
  };

  // Control device (on/off)
  const controlDevice = async (deviceId: number, action: 'on' | 'off') => {
    setControllingDevice(deviceId);
    try {
      const result = await api.post<TuyaDeviceControlResponse>(
        endpoints.tuyaDeviceControl(deviceId),
        { action: action === 'on' ? 'turn_on' : 'turn_off' }
      );

      if (result.success) {
        setDevices(prev =>
          prev.map(device =>
            device.id === deviceId
              ? { ...device, power_state: result.power_state, last_control_at: new Date().toISOString() }
              : device
          )
        );
      }
    } catch (err: any) {
      console.error('Failed to control device:', err);
      const errorMsg = err.message || '';
      if (errorMsg.includes('Tuya Cloud not initialized') || errorMsg.includes('API credentials')) {
        setError('Tuya Cloud API yapılandırılmamış. Lütfen "API Ayarları" butonuna tıklayarak yapılandırın.');
      } else {
        setError('Cihaz kontrol edilirken bir hata oluştu');
      }
    } finally {
      setControllingDevice(null);
    }
  };

  // Toggle device
  const toggleDevice = async (deviceId: number) => {
    setControllingDevice(deviceId);
    try {
      const result = await api.post<TuyaDeviceControlResponse>(
        endpoints.tuyaDeviceToggle(deviceId)
      );

      if (result.success) {
        setDevices(prev =>
          prev.map(device =>
            device.id === deviceId
              ? { ...device, power_state: result.power_state, last_control_at: new Date().toISOString() }
              : device
          )
        );
      }
    } catch (err) {
      console.error('Failed to toggle device:', err);
      setError('Cihaz değiştirilirken bir hata oluştu');
    } finally {
      setControllingDevice(null);
    }
  };

  // Delete device
  const deleteDevice = async (deviceId: number) => {
    if (!confirm('Bu cihazı silmek istediğinizden emin misiniz?')) return;

    try {
      await api.delete(endpoints.tuyaDevice(deviceId));
      setDevices(prev => prev.filter(device => device.id !== deviceId));
    } catch (err) {
      console.error('Failed to delete device:', err);
      setError('Cihaz silinirken bir hata oluştu');
    }
  };

  // Refresh device status
  const refreshStatus = async (deviceId: number) => {
    try {
      const data = await api.get<TuyaDeviceStatusResponse>(endpoints.tuyaDeviceStatus(deviceId));
      setDevices(prev =>
        prev.map(device =>
          device.id === deviceId
            ? { ...device, is_online: data.is_online, power_state: data.power_state, last_seen_at: data.last_seen_at }
            : device
        )
      );
    } catch (err) {
      console.error('Failed to refresh device status:', err);
    }
  };

  // Restart device (smart restart with automatic strategy selection)
  const restartDevice = async (deviceId: number, delaySeconds: number = 5) => {
    setRestartingDevice(deviceId);
    setError(null);
    try {
      const result = await api.post<TuyaDeviceControlResponse>(
        `${endpoints.tuyaDeviceRestart(deviceId)}?delay_seconds=${delaySeconds}`
      );

      if (result.success) {
        // Show success message based on strategy and result
        let message = result.message || 'Cihaz yeniden başlatıldı';
        
        // For timer strategy, show scheduled times
        if (result.strategy === 'timer') {
          message = result.message || 'Zamanlayıcılar oluşturuldu. Cihaz 2 dk sonra kapanıp 3 dk sonra açılacak.';
        }
        
        // For sequential strategy with turn_on_failed flag
        if (result.strategy === 'sequential' && result.turn_on_failed) {
          message = result.message || 'Cihaz kapatıldı. Tekrar açma başarısız oldu (internet bağlantısı kesildi). Cihazı manuel olarak açmanız gerekebilir.';
        }
        
        setError(null);
        
        // Update device state
        setDevices(prev =>
          prev.map(device =>
            device.id === deviceId
              ? { ...device, power_state: result.power_state, last_control_at: new Date().toISOString() }
              : device
          )
        );
        
        // For timer strategy, refresh after 3 minutes to show final state
        if (result.strategy === 'timer') {
          setTimeout(() => {
            refreshStatus(deviceId);
          }, 3.5 * 60 * 1000); // 3.5 minutes
        }
        
        // For countdown strategy, refresh after delay to show final state
        if (result.strategy === 'countdown') {
          setTimeout(() => {
            refreshStatus(deviceId);
          }, (delaySeconds + 2) * 1000);
        }
        
        // For sequential strategy with turn_on_failed, also refresh after delay
        if (result.strategy === 'sequential' && result.turn_on_failed) {
          setTimeout(() => {
            refreshStatus(deviceId);
          }, (delaySeconds + 2) * 1000);
        }
      }
    } catch (err: any) {
      console.error('Failed to restart device:', err);
      const errorMsg = err.message || 'Cihaz yeniden başlatılırken bir hata oluştu';
      setError(errorMsg);
    } finally {
      setRestartingDevice(null);
    }
  };

  // Fetch Tuya config on mount
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const config = await api.get<TuyaConfigResponse>(endpoints.tuyaConfig);
        setTuyaConfig(config);
        setConfigForm({
          access_id: config.access_id,
          access_secret: '',
          api_region: config.api_region,
        });
      } catch (err) {
        console.error('Failed to fetch Tuya config:', err);
      }
    };
    fetchConfig();
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchDevices();
  }, [fetchDevices]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(fetchDevices, 30000);
    return () => clearInterval(interval);
  }, [fetchDevices]);

  // Format date
  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('tr-TR');
  };

  // Save Tuya config
  const saveConfig = async () => {
    if (!configForm.access_id || !configForm.access_secret) {
      setError('Access ID ve Access Secret alanları zorunludur');
      return;
    }

    setIsSavingConfig(true);
    setError(null);
    try {
      const result = await api.post<TuyaConfigResponse>(endpoints.tuyaConfig, configForm);
      setTuyaConfig(result);
      setIsConfigDialogOpen(false);
      // Refresh devices after config update
      await fetchDevices();
    } catch (err: any) {
      console.error('Failed to save Tuya config:', err);
      setError(err.message || 'Tuya yapılandırması kaydedilirken bir hata oluştu');
    } finally {
      setIsSavingConfig(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Akıllı Prizler</h1>
          <p className="text-muted-foreground">
            Tuya akıllı prizlerinizi yönetin ve kontrol edin
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={fetchDevices}
            disabled={isLoading}
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Yenile
          </Button>
          <Button
            variant="outline"
            onClick={discoverDevices}
            disabled={isDiscovering || !tuyaConfig?.is_configured}
          >
            {isDiscovering ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Cloud className="mr-2 h-4 w-4" />
            )}
            Cloud'dan Getir
          </Button>
          <Button
            variant="outline"
            onClick={() => setIsConfigDialogOpen(true)}
          >
            <Settings className="mr-2 h-4 w-4" />
            API Ayarları
          </Button>
          <Button onClick={() => setIsAddDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Cihaz Ekle
          </Button>
        </div>
      </div>

      {/* Config Status Banner */}
      {tuyaConfig && (
        <Card className={tuyaConfig.is_configured ? 'border-green-500 bg-green-50 dark:bg-green-950/20' : 'border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20'}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {tuyaConfig.is_configured ? (
                  <>
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                    <div>
                      <p className="font-medium text-green-900 dark:text-green-100">
                        Tuya Cloud API Yapılandırıldı
                      </p>
                      <p className="text-sm text-green-700 dark:text-green-300">
                        Access ID: {tuyaConfig.access_id} | Region: {tuyaConfig.api_region.toUpperCase()}
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-5 w-5 text-yellow-600" />
                    <div>
                      <p className="font-medium text-yellow-900 dark:text-yellow-100">
                        Tuya Cloud API Yapılandırması Gerekli
                      </p>
                      <p className="text-sm text-yellow-700 dark:text-yellow-300">
                        Cihazları Cloud'dan çekmek için API bilgilerinizi girin
                      </p>
                    </div>
                  </>
                )}
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsConfigDialogOpen(true)}
              >
                <Settings className="mr-2 h-4 w-4" />
                Yapılandır
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error Message */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="p-4">
            <p className="text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Toplam Cihaz</CardTitle>
            <Plug className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{devices.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Online</CardTitle>
            <Wifi className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {devices.filter(d => d.is_online).length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Offline</CardTitle>
            <WifiOff className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {devices.filter(d => !d.is_online).length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Açık Olanlar</CardTitle>
            <Power className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">
              {devices.filter(d => d.power_state).length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Devices Grid */}
      {isLoading && devices.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center">
            <RefreshCw className="mx-auto h-8 w-8 animate-spin text-muted-foreground" />
            <p className="mt-2 text-muted-foreground">Cihazlar yükleniyor...</p>
          </CardContent>
        </Card>
      ) : devices.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center">
            <Plug className="mx-auto h-12 w-12 text-muted-foreground" />
            <h3 className="mt-4 text-lg font-semibold">Henüz cihaz eklenmemiş</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              {tuyaConfig?.is_configured
                ? 'Tuya Cloud\'dan cihaz çekmek için "Cloud\'dan Getir" butonuna tıklayın veya manuel olarak cihaz ekleyin'
                : 'Önce Tuya Cloud API bilgilerinizi yapılandırın, ardından cihazlarınızı Cloud\'dan çekin'}
            </p>
            <div className="mt-4 flex justify-center gap-2">
              {tuyaConfig?.is_configured && (
                <Button variant="outline" onClick={discoverDevices} disabled={isDiscovering}>
                  {isDiscovering ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Cloud className="mr-2 h-4 w-4" />
                  )}
                  Cloud\'dan Getir
                </Button>
              )}
              <Button onClick={() => setIsAddDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Manuel Ekle
              </Button>
              {!tuyaConfig?.is_configured && (
                <Button variant="outline" onClick={() => setIsConfigDialogOpen(true)}>
                  <Settings className="mr-2 h-4 w-4" />
                  API Ayarları
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {devices.map((device) => (
            <Card
              key={device.id}
              className={`transition-all hover:shadow-lg ${
                device.power_state ? 'border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20' : ''
              }`}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="flex items-center gap-2">
                      <Plug className="h-5 w-5" />
                      {device.name}
                    </CardTitle>
                    <CardDescription className="mt-1">
                      {device.device_id}
                    </CardDescription>
                  </div>
                  <Badge variant={device.is_online ? 'success' : 'destructive'}>
                    {device.is_online ? (
                      <>
                        <Wifi className="mr-1 h-3 w-3" />
                        Online
                      </>
                    ) : (
                      <>
                        <WifiOff className="mr-1 h-3 w-3" />
                        Offline
                      </>
                    )}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Power State */}
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Güç Durumu:</span>
                  <Badge variant={device.power_state ? 'success' : 'secondary'}>
                    {device.power_state ? (
                      <>
                        <ToggleRight className="mr-1 h-4 w-4" />
                        Açık
                      </>
                    ) : (
                      <>
                        <ToggleLeft className="mr-1 h-4 w-4" />
                        Kapalı
                      </>
                    )}
                  </Badge>
                </div>

                {/* Device Type */}
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Cihaz Tipi:</span>
                  <span className="text-sm font-medium">
                    {device.device_type === 'SMART_PLUG' ? 'Akıllı Priz' :
                     device.device_type === 'SMART_SWITCH' ? 'Akıllı Anahtar' :
                     device.device_type === 'SMART_BULB' ? 'Akıllı Ampul' :
                     device.device_type}
                  </span>
                </div>

                {/* Last Seen */}
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Son Görülme:</span>
                  <span className="text-xs">{formatDate(device.last_seen_at)}</span>
                </div>

                {/* Last Control */}
                {device.last_control_at && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Son Kontrol:</span>
                    <span className="text-xs">{formatDate(device.last_control_at)}</span>
                  </div>
                )}

                {/* Product Info */}
                {device.product_name && (
                  <div className="rounded-md bg-muted p-2">
                    <p className="text-xs font-medium">{device.product_name}</p>
                    <p className="text-xs text-muted-foreground">{device.product_id}</p>
                  </div>
                )}

                {/* Actions */}
                <div className="flex flex-col gap-2 pt-2">
                  <div className="flex gap-2">
                    <Button
                      variant={device.power_state ? 'destructive' : 'default'}
                      size="sm"
                      className="flex-1"
                      onClick={() => controlDevice(device.id, device.power_state ? 'off' : 'on')}
                      disabled={controllingDevice === device.id || restartingDevice === device.id}
                    >
                      <Power className="mr-2 h-4 w-4" />
                      {device.power_state ? 'Kapat' : 'Aç'}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => toggleDevice(device.id)}
                      disabled={controllingDevice === device.id || restartingDevice === device.id}
                    >
                      <RefreshCw className={`h-4 w-4 ${controllingDevice === device.id ? 'animate-spin' : ''}`} />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => refreshStatus(device.id)}
                      disabled={controllingDevice === device.id || restartingDevice === device.id}
                      title="Durumu Cloud'dan Yenile"
                    >
                      <Wifi className={`h-4 w-4 ${controllingDevice === device.id ? 'animate-spin' : ''}`} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deleteDevice(device.id)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className={`w-full ${!device.is_online ? 'opacity-50' : ''}`}
                    onClick={() => restartDevice(device.id)}
                    disabled={controllingDevice === device.id || restartingDevice === device.id || !device.is_online}
                    title={device.is_online ? 'Yeniden Başlat (Kapat → 5sn bekle → Aç)' : 'Cihaz offline - restart için cihazın online olması gerekiyor'}
                  >
                    {restartingDevice === device.id ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Yeniden Başlatılıyor...
                      </>
                    ) : (
                      <>
                        <RotateCcw className="mr-2 h-4 w-4" />
                        {device.is_online ? 'Yeniden Başlat' : 'Yeniden Başlat (Offline)'}
                      </>
                    )}
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    className="w-full"
                    onClick={() => router.push(`/tuya-devices/${device.id}`)}
                  >
                    <ExternalLink className="mr-2 h-4 w-4" />
                    Detay ve Geçmiş
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Add Device Dialog */}
      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Yeni Cihaz Ekle</DialogTitle>
            <DialogDescription>
              Tuya cihazınızı manuel olarak ekleyin. Device ID ve diğer bilgileri Tuya IoT platformundan alabilirsiniz.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="device_id">Device ID *</Label>
              <Input
                id="device_id"
                placeholder="örn: 35004015483fda08ac54"
                value={newDevice.device_id || ''}
                onChange={(e) => setNewDevice({ ...newDevice, device_id: e.target.value })}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="name">İsim *</Label>
              <Input
                id="name"
                placeholder="örn: Salon Prizi"
                value={newDevice.name || ''}
                onChange={(e) => setNewDevice({ ...newDevice, name: e.target.value })}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="device_type">Cihaz Tipi</Label>
              <Input
                id="device_type"
                placeholder="SMART_PLUG"
                value={newDevice.device_type || 'SMART_PLUG'}
                onChange={(e) => setNewDevice({ ...newDevice, device_type: e.target.value })}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="local_key">Local Key (Opsiyonel)</Label>
              <Input
                id="local_key"
                placeholder="Tuya Cloud'dan alınır"
                value={newDevice.local_key || ''}
                onChange={(e) => setNewDevice({ ...newDevice, local_key: e.target.value })}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="ip_address">IP Adresi (Opsiyonel)</Label>
              <Input
                id="ip_address"
                placeholder="örn: 192.168.1.100"
                value={newDevice.ip_address || ''}
                onChange={(e) => setNewDevice({ ...newDevice, ip_address: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddDialogOpen(false)} disabled={isAdding}>
              İptal
            </Button>
            <Button onClick={addDevice} disabled={isAdding}>
              {isAdding ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Ekleniyor...
                </>
              ) : (
                'Ekle'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Discover Dialog */}
      <Dialog open={isDiscoverDialogOpen} onOpenChange={setIsDiscoverDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Cloud\'dan Bulunan Cihazlar</DialogTitle>
            <DialogDescription>
              Tuya Cloud hesabınızda bulunan cihazlar. Eklemek istediğiniz cihazları seçin.
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-96 overflow-y-auto">
            {discoveredDevices.length === 0 ? (
              <div className="py-8 text-center text-muted-foreground">
                Bulunan cihaz yok. Tüm cihazlar zaten eklenmiş olabilir veya API yapılandırması hatalı.
              </div>
            ) : (
              <div className="grid gap-2">
                {discoveredDevices.map((device) => (
                  <Card key={device.device_id} className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <h4 className="font-medium">{device.name}</h4>
                        <p className="text-sm text-muted-foreground">{device.device_id}</p>
                        <p className="text-xs text-muted-foreground">{device.product_name}</p>
                        <div className="mt-1 flex gap-2">
                          <Badge variant={device.is_online ? 'success' : 'secondary'}>
                            {device.is_online ? 'Online' : 'Offline'}
                          </Badge>
                          {device.ip && (
                            <Badge variant="outline">{device.ip}</Badge>
                          )}
                        </div>
                      </div>
                      <Button onClick={() => addDiscoveredDevice(device)}>
                        <Plus className="mr-2 h-4 w-4" />
                        Ekle
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDiscoverDialogOpen(false)}>
              Kapat
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Config Dialog */}
      <Dialog open={isConfigDialogOpen} onOpenChange={setIsConfigDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Tuya Cloud API Ayarları</DialogTitle>
            <DialogDescription>
              Tuya IoT Platformundan aldığınız API bilgilerini girin. Bu bilgiler Cloud üzerinden cihaz yönetimi için gereklidir.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="access_id">Access ID *</Label>
              <Input
                id="access_id"
                placeholder="örn: tuya_xxxxxxxxxxxxx"
                value={configForm.access_id}
                onChange={(e) => setConfigForm({ ...configForm, access_id: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                Tuya IoT Platform &gt; Cloud &gt; API Ayarları bölümünden alabilirsiniz
              </p>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="access_secret">Access Secret *</Label>
              <Input
                id="access_secret"
                type="password"
                placeholder="••••••••••••••••"
                value={configForm.access_secret}
                onChange={(e) => setConfigForm({ ...configForm, access_secret: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                {tuyaConfig?.has_access_secret && !configForm.access_secret
                  ? 'Mevcut secret korunuyor, değiştirmek için yeni değer girin'
                  : 'Tuya IoT Platform\'dan aldığınız Access Secret'}
              </p>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="api_region">API Region</Label>
              <select
                id="api_region"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={configForm.api_region}
                onChange={(e) => setConfigForm({ ...configForm, api_region: e.target.value })}
              >
                <option value="eu">Europe (eu)</option>
                <option value="us">United States (us)</option>
                <option value="cn">China (cn)</option>
                <option value="in">India (in)</option>
              </select>
              <p className="text-xs text-muted-foreground">
                Tuya Cloud hesabınızın bölgesini seçin
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsConfigDialogOpen(false)} disabled={isSavingConfig}>
              İptal
            </Button>
            <Button onClick={saveConfig} disabled={isSavingConfig}>
              {isSavingConfig ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Kaydediliyor...
                </>
              ) : (
                'Kaydet'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
