'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { MODBUS_METHODS } from '@/lib/constants';

export default function AddDevicePage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    device_code: '',
    modem_id: '',
    device_addr: '',
    name: '',
    location: '',
    method_no: '0',
  });

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      // API call will go here
      console.log('Creating device:', formData);
      router.push('/devices');
    } catch (error) {
      console.error('Error creating device:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const updateField = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Yeni Cihaz Ekle</h1>
          <p className="text-muted-foreground">Sisteme yeni bir su otomatı cihazı ekleyin</p>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit}>
        <Card>
          <CardHeader>
            <CardTitle>Cihaz Bilgileri</CardTitle>
            <CardDescription>Cihazın temel bilgilerini girin</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="device_code">Cihaz Kodu *</Label>
                <Input
                  id="device_code"
                  placeholder="M1, M2, M3..."
                  value={formData.device_code}
                  onChange={(e) => updateField('device_code', e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="name">Cihaz Adı *</Label>
                <Input
                  id="name"
                  placeholder="Merkez Cihaz 1"
                  value={formData.name}
                  onChange={(e) => updateField('name', e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="modem_id">Modem ID *</Label>
                <Input
                  id="modem_id"
                  placeholder="00001276"
                  value={formData.modem_id}
                  onChange={(e) => updateField('modem_id', e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="device_addr">Modbus Adres *</Label>
                <Input
                  id="device_addr"
                  type="number"
                  placeholder="1"
                  value={formData.device_addr}
                  onChange={(e) => updateField('device_addr', e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="location">Konum</Label>
                <Input
                  id="location"
                  placeholder="Ana Bina Giriş"
                  value={formData.location}
                  onChange={(e) => updateField('location', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Modbus Methodu</Label>
                <Select value={formData.method_no} onValueChange={(val) => updateField('method_no', val)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {MODBUS_METHODS.map((m) => (
                      <SelectItem key={m.value} value={String(m.value)}>
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-4">
              <Button type="button" variant="outline" onClick={() => router.back()}>
                İptal
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Kaydediliyor...
                  </>
                ) : (
                  'Cihaz Ekle'
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
}
