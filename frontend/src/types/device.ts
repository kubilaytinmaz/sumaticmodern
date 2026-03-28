export type DeviceStatus = 'ONLINE' | 'OFFLINE' | 'PENDING';

export interface Device {
  id: number;
  device_code: string;
  modem_id: string;
  device_addr: number;
  name: string;
  location: string | null;
  method_no: number;
  reg_offset_json: Record<string, unknown>;
  alias_json: Record<string, unknown>;
  skip_raw_json: unknown[];
  is_enabled: boolean;
  is_pending: boolean;
  last_seen_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  status?: DeviceStatus;
  is_online?: boolean;  // Computed field for backward compatibility
  latest_reading?: DeviceReading;
}

export interface DeviceCreate {
  device_code: string;
  modem_id: string;
  device_addr: number;
  name: string;
  location?: string;
  method_no?: number;
  reg_offset_json?: Record<string, unknown>;
  alias_json?: Record<string, unknown>;
  skip_raw_json?: unknown[];
  is_enabled?: boolean;
}

export interface DeviceUpdate {
  name?: string;
  location?: string;
  method_no?: number;
  reg_offset_json?: Record<string, unknown>;
  alias_json?: Record<string, unknown>;
  skip_raw_json?: unknown[];
  is_enabled?: boolean;
}

export interface DeviceReading {
  id: number;
  device_id: number;
  timestamp: string;
  counter_19l: number | null;
  counter_5l: number | null;
  output_1_status: number | null;
  output_2_status: number | null;
  fault_status: number;
  program_1_time: number | null;
  program_2_time: number | null;
  program_1_coin_count: number | null;
  program_2_coin_count: number | null;
  output3_input1_time: number | null;
  output3_input2_time: number | null;
  counter_total_low: number | null;
  counter_total_high: number | null;
  modbus_address: number | null;
  device_password: number | null;
  raw_data: Record<string, unknown> | null;
  is_spike: boolean;
}

export interface DeviceStatusHistory {
  id: number;
  device_id: number;
  status: DeviceStatus;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
  reason: string | null;
  metadata: Record<string, unknown>;
}

export interface DeviceSummary {
  device: Device;
  today_revenue_19l: number;
  today_revenue_5l: number;
  today_revenue_total: number;
  month_revenue_19l: number;
  month_revenue_5l: number;
  month_revenue_total: number;
  online_duration_hours: number;
  offline_duration_hours: number;
}
