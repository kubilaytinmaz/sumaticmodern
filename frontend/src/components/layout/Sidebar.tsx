'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Monitor,
  Settings,
  Droplets,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  List,
  Activity,
  Database,
  Plug,
  TrendingUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useState, useEffect } from 'react';

interface Device {
  id: number;
  device_code: string;
  name: string;
  is_online: boolean;
}

const navigation = [
  {
    name: 'Dashboard',
    href: '/',
    icon: LayoutDashboard,
  },
  {
    name: 'Canlı Veri',
    href: '/live-data',
    icon: Database,
  },
  {
    name: 'Aylık Ciro',
    href: '/monthly-revenue',
    icon: TrendingUp,
  },
  {
    name: 'Akıllı Prizler',
    href: '/tuya-devices',
    icon: Plug,
  },
  {
    name: 'MQTT Loglar',
    href: '/mqtt-logs',
    icon: Activity,
  },
  {
    name: 'Ayarlar',
    href: '/settings',
    icon: Settings,
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [devicesExpanded, setDevicesExpanded] = useState(true);
  const [devices, setDevices] = useState<Device[]>([]);
  const [isLoadingDevices, setIsLoadingDevices] = useState(false);

  // Compute online/offline from devices list
  const onlineCount = devices.filter(d => d.is_online).length;
  const offlineCount = devices.length - onlineCount;

  // Fetch devices from API
  useEffect(() => {
    const fetchDevices = async () => {
      setIsLoadingDevices(true);
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
        setIsLoadingDevices(false);
      }
    };

    fetchDevices();
    // Refresh devices every 30 seconds
    const interval = setInterval(fetchDevices, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <aside
      className={cn(
        'flex flex-col border-r border-sidebar-border bg-sidebar transition-all duration-300',
        collapsed ? 'w-[68px]' : 'w-[260px]'
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center border-b border-sidebar-border px-4">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Droplets className="h-5 w-5 text-primary-foreground" />
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="text-sm font-bold text-sidebar-foreground">
                Su Otomatları
              </span>
              <span className="text-[10px] text-muted-foreground">
                Uzak Takip
              </span>
            </div>
          )}
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4 overflow-y-auto">
        {/* Devices Section */}
        {collapsed ? (
          <Link
            href="/devices"
            className={cn(
              'flex items-center justify-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
              pathname.startsWith('/devices')
                ? 'bg-sidebar-accent text-sidebar-primary'
                : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground'
            )}
            title="Cihazlar"
          >
            <Monitor className={cn('h-5 w-5 shrink-0', pathname.startsWith('/devices') && 'text-sidebar-primary')} />
          </Link>
        ) : (
          <div className="space-y-1">
            {/* Devices Header */}
            <button
              onClick={() => setDevicesExpanded(!devicesExpanded)}
              className={cn(
                'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                pathname.startsWith('/devices')
                  ? 'text-sidebar-primary'
                  : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground'
              )}
            >
              <Monitor className="h-5 w-5 shrink-0" />
              <span className="flex-1 text-left">Cihazlar</span>
              {devicesExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>

            {/* Devices Submenu */}
            {devicesExpanded && (
              <div className="ml-4 space-y-1 border-l border-sidebar-border pl-2">
                {/* All Devices Link */}
                <Link
                  href="/devices/all-devices"
                  className={cn(
                    'flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors',
                    pathname === '/devices/all-devices' || pathname.startsWith('/devices/all-devices')
                      ? 'bg-sidebar-accent text-sidebar-primary font-medium'
                      : 'text-sidebar-foreground/60 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground'
                  )}
                >
                  <List className="h-4 w-4 shrink-0" />
                  <span>Tüm Cihazlar</span>
                  <Badge variant="secondary" className="ml-auto text-xs">
                    {devices.length}
                  </Badge>
                </Link>

                {/* Individual Devices */}
                {isLoadingDevices ? (
                  <div className="px-3 py-2 text-xs text-muted-foreground">
                    Yükleniyor...
                  </div>
                ) : (
                  devices.map((device) => (
                    <Link
                      key={device.id}
                      href={`/devices/${device.id}`}
                      className={cn(
                        'flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors group',
                        pathname === `/devices/${device.id}`
                          ? 'bg-sidebar-accent text-sidebar-primary font-medium'
                          : 'text-sidebar-foreground/60 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground'
                      )}
                      title={device.name}
                    >
                      <div
                        className={cn(
                          'h-2 w-2 rounded-full shrink-0',
                          device.is_online ? 'bg-green-500' : 'bg-red-500'
                        )}
                      />
                      <span className="truncate flex-1">{device.device_code}</span>
                    </Link>
                  ))
                )}
              </div>
            )}
          </div>
        )}

        {navigation.map((item) => {
          const isActive =
            item.href === '/'
              ? pathname === '/'
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-sidebar-accent text-sidebar-primary'
                  : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground'
              )}
              title={collapsed ? item.name : undefined}
            >
              <item.icon className={cn('h-5 w-5 shrink-0', isActive && 'text-sidebar-primary')} />
              {!collapsed && <span>{item.name}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Device Status Summary */}
      {!collapsed && (
        <div className="mx-3 mb-4 rounded-lg border border-sidebar-border bg-sidebar-accent/30 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Cihaz Durumu
          </p>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-2.5 w-2.5 rounded-full bg-green-500 pulse-online" />
              <span className="text-sm text-sidebar-foreground">{onlineCount} Online</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-2.5 w-2.5 rounded-full bg-red-500 pulse-offline" />
              <span className="text-sm text-sidebar-foreground">{offlineCount} Offline</span>
            </div>
          </div>
        </div>
      )}

      {/* Collapse Toggle */}
      <div className="border-t border-sidebar-border p-3">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-center text-muted-foreground hover:text-sidebar-foreground"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4" />
              <span className="text-xs">Daralt</span>
            </>
          )}
        </Button>
      </div>
    </aside>
  );
}
