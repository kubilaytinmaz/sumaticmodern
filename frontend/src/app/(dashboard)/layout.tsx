'use client';

import { Sidebar } from '@/components/layout/Sidebar';
import { Navbar } from '@/components/layout/Navbar';
import { useWebSocket } from '@/hooks/useWebSocket';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { isConnected } = useWebSocket();

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Navbar isConnected={isConnected} alertCount={0} />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
