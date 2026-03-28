'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Search, Filter, MoreHorizontal, Eye, Edit, Trash2, RefreshCw, Layers } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatRelativeTime, getStatusBgColor, formatMoney } from '@/lib/utils';

interface DeviceFromAPI {
  id: number;
  device_code: string;
  name: string;
  modem_id: string;
  device_addr: number;
  last_reading_at: string | null;
  counter_19l: number;
  counter_5l: number;
  total: number;
  fault_status: number;
  is_online: boolean;
}

export default function DevicesPage() {
  const router = useRouter();
  const [search, setSearch] = useState('');
  const [devices, setDevices] = useState<DeviceFromAPI[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch devices from API
  useEffect(() => {
    const fetchDevices = async () => {
      setIsLoading(true);
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/api/v1/charts/devices/summary`);
        if (res.ok) {
          const data = await res.json();
          setDevices(data.devices || []);
        }
      } catch (error) {
        console.error('Failed to fetch devices:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDevices();
  }, []);

  const filteredDevices = devices.filter(
    (device) =>
      device.name.toLowerCase().includes(search.toLowerCase()) ||
      device.device_code.toLowerCase().includes(search.toLowerCase()) ||
      device.modem_id.toLowerCase().includes(search.toLowerCase())
  );

  const handleRefresh = () => {
    window.location.reload();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Cihazlar</h1>
          <p className="text-muted-foreground">
            Tüm su otomatı cihazlarını yönetin ({devices.length} cihaz)
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => router.push('/devices/all-devices')}>
            <Layers className="mr-2 h-4 w-4" />
            Tüm Cihazlar
          </Button>
          <Button variant="outline" onClick={handleRefresh}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Yenile
          </Button>
          <Button onClick={() => router.push('/devices/add')}>
            <Plus className="mr-2 h-4 w-4" />
            Yeni Cihaz
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Filtreler</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Cihaz ara (isim, kod, modem ID)..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Button variant="outline">
              <Filter className="mr-2 h-4 w-4" />
              Filtrele
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">Yükleniyor...</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Kod</TableHead>
                  <TableHead>İsim</TableHead>
                  <TableHead>Modem ID</TableHead>
                  <TableHead className="text-right">Sayaç 1 (19L)</TableHead>
                  <TableHead className="text-right">Sayaç 2 (5L)</TableHead>
                  <TableHead className="text-right">Toplam</TableHead>
                  <TableHead>Durum</TableHead>
                  <TableHead>Son Görülme</TableHead>
                  <TableHead className="text-right">İşlemler</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {/* Tüm Cihazlar Satırı */}
                <TableRow
                  className="cursor-pointer hover:bg-primary/5 bg-primary/5 border-b-2 border-primary/20 font-bold"
                  onClick={() => router.push('/devices/all-devices')}
                >
                  <TableCell className="font-bold text-primary">
                    <div className="flex items-center gap-2">
                      <Layers className="h-4 w-4" />
                      TÜMÜ
                    </div>
                  </TableCell>
                  <TableCell className="font-bold text-primary">Tüm Cihazlar</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">{devices.length} cihaz</TableCell>
                  <TableCell className="text-right font-bold">{formatMoney(devices.reduce((sum, d) => sum + d.counter_19l, 0))}</TableCell>
                  <TableCell className="text-right font-bold">{formatMoney(devices.reduce((sum, d) => sum + d.counter_5l, 0))}</TableCell>
                  <TableCell className="text-right font-bold text-primary">{formatMoney(devices.reduce((sum, d) => sum + d.total, 0))}</TableCell>
                  <TableCell>
                    <Badge className="bg-blue-600 text-white hover:bg-blue-700">
                      {devices.filter(d => d.is_online).length}/{devices.length} Aktif
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground text-xs">—</TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="icon" onClick={(e) => { e.stopPropagation(); router.push('/devices/all-devices'); }}>
                      <Eye className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>

                {filteredDevices.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                      Cihaz bulunamadı
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredDevices.map((device) => (
                    <TableRow key={device.id} className="cursor-pointer hover:bg-muted/50" onClick={() => router.push(`/devices/${device.id}`)}>
                      <TableCell className="font-medium">{device.device_code}</TableCell>
                      <TableCell className="font-medium">{device.name}</TableCell>
                      <TableCell className="font-mono text-xs">{device.modem_id}</TableCell>
                      <TableCell className="text-right">{formatMoney(device.counter_19l)}</TableCell>
                      <TableCell className="text-right">{formatMoney(device.counter_5l)}</TableCell>
                      <TableCell className="text-right font-medium">{formatMoney(device.total)}</TableCell>
                      <TableCell>
                        <Badge className={getStatusBgColor(device.is_online ? 'ONLINE' : 'OFFLINE')}>
                          {device.is_online ? 'Çevrimiçi' : 'Çevrimdışı'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-xs">
                        {device.last_reading_at ? formatRelativeTime(device.last_reading_at) : '-'}
                      </TableCell>
                      <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => router.push(`/devices/${device.id}`)}>
                              <Eye className="mr-2 h-4 w-4" />
                              Görüntüle
                            </DropdownMenuItem>
                            <DropdownMenuItem>
                              <Edit className="mr-2 h-4 w-4" />
                              Düzenle
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem className="text-destructive">
                              <Trash2 className="mr-2 h-4 w-4" />
                              Sil
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
