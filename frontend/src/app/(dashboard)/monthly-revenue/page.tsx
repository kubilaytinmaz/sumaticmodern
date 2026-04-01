'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Calendar, TrendingUp, DollarSign } from 'lucide-react';
import { api, endpoints } from '@/lib/api';
import { formatMoney } from '@/lib/utils';
import type { MonthlyRevenueRecord, MonthlyRevenueSummary, ActiveCycleRevenue } from '@/types/monthly_revenue';

const monthNames = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];

export default function MonthlyRevenuePage() {
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [revenueData, setRevenueData] = useState<MonthlyRevenueRecord[]>([]);
  const [activeCycles, setActiveCycles] = useState<ActiveCycleRevenue[]>([]);
  const [summary, setSummary] = useState<MonthlyRevenueSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showActive, setShowActive] = useState(true);

  useEffect(() => {
    fetchData();
  }, [selectedYear, selectedMonth, showActive]);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      if (showActive) {
        // Aktif döngü cirolarını getir
        const activeData = await api.get<ActiveCycleRevenue[]>(endpoints.monthlyRevenueActive);
        setActiveCycles(activeData);
        
        // Mevcut ay özetini getir
        const now = new Date();
        const summaryData = await api.get<MonthlyRevenueSummary>(
          endpoints.monthlyRevenueSummary(now.getFullYear(), now.getMonth() + 1)
        );
        setSummary(summaryData);
      } else {
        // Seçilen ayın kapanmış cirolarını getir
        const historyData = await api.get<MonthlyRevenueRecord[]>(
          `${endpoints.monthlyRevenueHistory}?year=${selectedYear}&month=${selectedMonth}`
        );
        setRevenueData(historyData);
        
        // Özet verilerini getir
        const summaryData = await api.get<MonthlyRevenueSummary>(
          endpoints.monthlyRevenueSummary(selectedYear, selectedMonth)
        );
        setSummary(summaryData);
      }
    } catch (error) {
      console.error('Failed to fetch monthly revenue:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const totalRevenue = showActive
    ? activeCycles.reduce((sum, d) => sum + d.current_revenue, 0)
    : revenueData.reduce((sum, d) => sum + d.total_revenue, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Aylık Ciro Raporu</h1>
          <p className="text-muted-foreground">
            Tüm cihazların aylık ciro kayıtları
          </p>
        </div>
        <div className="flex gap-2">
          <Select value={showActive ? 'active' : 'closed'} onValueChange={(v) => setShowActive(v === 'active')}>
            <SelectTrigger className="w-[150px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="active">Aktif Döngü</SelectItem>
              <SelectItem value="closed">Kapanmış Ay</SelectItem>
            </SelectContent>
          </Select>
          
          {!showActive && (
            <>
              <Select value={selectedYear.toString()} onValueChange={(v) => setSelectedYear(parseInt(v))}>
                <SelectTrigger className="w-[120px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[2025, 2026, 2027, 2028].map(year => (
                    <SelectItem key={year} value={year.toString()}>{year}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={selectedMonth.toString()} onValueChange={(v) => setSelectedMonth(parseInt(v))}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {monthNames.map((m, i) => (
                    <SelectItem key={i + 1} value={(i + 1).toString()}>{m}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {showActive ? 'Aktif Döngü Ciro' : 'Seçilen Ay Ciro'}
            </CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{formatMoney(totalRevenue)}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {showActive ? 'Mevcut ay aktif döngü' : `${monthNames[selectedMonth - 1]} ${selectedYear}`}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Cihaz Sayısı
            </CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{showActive ? activeCycles.length : revenueData.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Toplam cihaz
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Durum
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {showActive ? (
                <Badge className="bg-blue-600">Aktif</Badge>
              ) : (
                <Badge variant={summary?.closed_count === summary?.device_count ? 'default' : 'secondary'}>
                  {summary?.closed_count || 0}/{summary?.device_count || 0} Kapatıldı
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {showActive ? 'Döngü devam ediyor' : 'Ay kapatma durumu'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Revenue Table */}
      <Card>
        <CardHeader>
          <CardTitle>
            {showActive ? 'Aktif Döngü Ciro Tablosu' : `${monthNames[selectedMonth - 1]} ${selectedYear} Ciro Tablosu`}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">Yükleniyor...</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Cihaz Kodu</TableHead>
                  <TableHead>Cihaz Adı</TableHead>
                  <TableHead className="text-right">19L Sayaç</TableHead>
                  <TableHead className="text-right">5L Sayaç</TableHead>
                  <TableHead className="text-right">Toplam Ciro</TableHead>
                  <TableHead>Durum</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(showActive ? activeCycles : revenueData).length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                      Veri bulunamadı
                    </TableCell>
                  </TableRow>
                ) : (
                  (showActive ? activeCycles : (revenueData as any[])).map((record: any) => (
                    <TableRow key={record.device_id}>
                      <TableCell className="font-medium">{record.device_code || `Cihaz ${record.device_id}`}</TableCell>
                      <TableCell>{record.device_name || '-'}</TableCell>
                      <TableCell className="text-right">
                        {formatMoney(showActive ? record.current_counter_19l : record.closing_counter_19l)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatMoney(showActive ? record.current_counter_5l : record.closing_counter_5l)}
                      </TableCell>
                      <TableCell className="text-right font-bold">
                        {formatMoney(showActive ? record.current_revenue : record.total_revenue)}
                      </TableCell>
                      <TableCell>
                        {showActive ? (
                          <Badge className="bg-blue-600">Aktif</Badge>
                        ) : (
                          <Badge variant={record.is_closed ? 'default' : 'secondary'}>
                            {record.is_closed ? 'Kapalı' : 'Aktif'}
                          </Badge>
                        )}
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
