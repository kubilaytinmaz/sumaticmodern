/**
 * Tuya Device Types
 * Matches backend schemas in backend/app/schemas/tuya_device.py
 */

export type TuyaDeviceType = 'SMART_PLUG' | 'SMART_SWITCH' | 'SMART_BULB' | 'OTHER';

export interface TuyaDevice {
  id: number;
  device_id: string;
  name: string;
  device_type: string;
  local_key: string | null;
  ip_address: string | null;
  is_enabled: boolean;
  is_online: boolean;
  power_state: boolean;
  last_seen_at: string | null;
  last_control_at: string | null;
  product_id: string | null;
  product_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface TuyaDeviceCreate {
  device_id: string;
  name: string;
  device_type: string;
  local_key?: string;
  ip_address?: string;
  is_enabled?: boolean;
  product_id?: string;
  product_name?: string;
}

export interface TuyaDeviceUpdate {
  name?: string;
  device_type?: string;
  local_key?: string;
  ip_address?: string;
  is_enabled?: boolean;
  product_id?: string;
  product_name?: string;
}

// Backend returns TuyaDeviceListResponse with "items" field
export interface TuyaDeviceListResponse {
  items: TuyaDevice[];
  total: number;
}

// Backend returns TuyaDeviceStatusResponse from /{device_id}/status
export interface TuyaDeviceStatusResponse {
  id: number;
  device_id: string;
  name: string;
  is_online: boolean;
  power_state: boolean;
  last_seen_at: string | null;
  last_control_at: string | null;
}

export interface TuyaDeviceControlRequest {
  action: 'turn_on' | 'turn_off' | 'toggle' | 'restart';
}

// Backend returns TuyaDeviceControlResponse from /{device_id}/control, /{device_id}/toggle, and /{device_id}/restart
export interface TuyaDeviceControlResponse {
  action?: string;
  success: boolean;
  power_state: boolean;
  message: string;
  strategy?: 'timer' | 'countdown' | 'relay_status' | 'sequential';
  delay_seconds?: number;
  turn_on_failed?: boolean; // True if sequential restart failed to turn device back on (modem/router control scenario)
}

export interface TuyaDiscoveredDevice {
  device_id: string;
  name: string;
  product_id: string;
  product_name: string;
  device_type: string;
  is_online: boolean;
  ip: string;
  local_key: string;
}

export interface TuyaDiscoveryResponse {
  devices: TuyaDiscoveredDevice[];
  total: number;
}

export interface TuyaServiceStatus {
  initialized: boolean;
  polling: boolean;
  cached_devices: number;
  api_region: string;
  has_credentials: boolean;
  access_id: string;
}

export interface TuyaConfig {
  access_id: string;
  access_secret: string;
  api_region: string;
}

export interface TuyaConfigResponse {
  access_id: string;
  api_region: string;
  has_access_secret: boolean;
  is_configured: boolean;
}

export interface TuyaDeviceControlLog {
  id: number;
  tuya_device_id: number;
  action: string;
  previous_state: boolean;
  new_state: boolean | null;
  success: boolean;
  error_message: string | null;
  performed_by: string | null;
  performed_at: string;
  created_at: string;
}

export interface TuyaDeviceControlHistoryResponse {
  items: TuyaDeviceControlLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface TuyaDeviceDetailsResponse extends TuyaDevice {
  recent_controls: TuyaDeviceControlLog[];
  total_controls: number;
  successful_controls: number;
  failed_controls: number;
}
