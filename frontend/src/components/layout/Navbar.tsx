'use client';

import { useRouter } from 'next/navigation';
import {
  Bell,
  LogOut,
  User,
  Settings,
  ChevronDown,
  Wifi,
  WifiOff,
  Sun,
  Moon,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/hooks/useAuth';
import { useTheme } from '@/components/theme-provider';
import { cn } from '@/lib/utils';

interface NavbarProps {
  isConnected?: boolean;
  alertCount?: number;
}

export function Navbar({ isConnected = false, alertCount = 0 }: NavbarProps) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout error:', error);
    }
    router.push('/login');
  };

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-background/95 px-6 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      {/* Left - Page title / Breadcrumbs */}
      <div className="flex items-center gap-4">
        <h2 className="text-lg font-semibold text-foreground">
          {/* Dynamic title can be set by page */}
        </h2>
      </div>

      {/* Right - Actions */}
      <div className="flex items-center gap-3">
        {/* Realtime Connection Status */}
        <div
          className={cn(
            'flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium',
            isConnected
              ? 'bg-green-500/10 text-green-500'
              : 'bg-red-500/10 text-red-500'
          )}
        >
          {isConnected ? (
            <>
              <Wifi className="h-3.5 w-3.5" />
              <span>Bağlı</span>
            </>
          ) : (
            <>
              <WifiOff className="h-3.5 w-3.5" />
              <span>Bağlantı Yok</span>
            </>
          )}
        </div>

        {/* Theme Toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          className="relative"
          title={theme === 'dark' ? 'Açık temaya geç' : 'Koyu temaya geç'}
        >
          {theme === 'dark' ? (
            <Sun className="h-5 w-5 text-muted-foreground transition-transform hover:text-foreground" />
          ) : (
            <Moon className="h-5 w-5 text-muted-foreground transition-transform hover:text-foreground" />
          )}
        </Button>

        {/* Notifications */}
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5 text-muted-foreground" />
          {alertCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] text-destructive-foreground">
              {alertCount > 9 ? '9+' : alertCount}
            </span>
          )}
        </Button>

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className="flex items-center gap-2 px-2 hover:bg-accent"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary">
                <User className="h-4 w-4" />
              </div>
              <div className="hidden flex-col items-start md:flex">
                <span className="text-sm font-medium">
                  {user?.full_name || user?.username || 'Kullanıcı'}
                </span>
                <span className="text-xs text-muted-foreground capitalize">
                  {user?.role === 'admin' ? 'Yönetici' : user?.role === 'user' ? 'Kullanıcı' : 'Görüntüleyici'}
                </span>
              </div>
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium">{user?.full_name || user?.username}</p>
                <p className="text-xs text-muted-foreground">{user?.email}</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => router.push('/settings')}>
              <Settings className="mr-2 h-4 w-4" />
              <span>Ayarlar</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout} className="text-destructive focus:text-destructive">
              <LogOut className="mr-2 h-4 w-4" />
              <span>Çıkış Yap</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
