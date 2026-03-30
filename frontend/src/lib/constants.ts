/**
 * Chart colors for data visualization
 */
export const CHART_COLORS = {
  primary: '#3b82f6',    // blue-500
  success: '#22c55e',    // green-500
  warning: '#f59e0b',    // amber-500
  danger: '#ef4444',     // red-500
  accent: '#f97316',     // orange-500
  info: '#06b6d4',       // cyan-500
  muted: '#6b7280',      // gray-500
} as const;

/**
 * Modbus method options for device configuration
 */
export const MODBUS_METHODS = [
  { value: 0, label: 'Method 0 - Okuma' },
  { value: 1, label: 'Method 1 - Okuma (Coil)' },
  { value: 2, label: 'Method 2 - Okuma (Discrete Input)' },
  { value: 3, label: 'Method 3 - Okuma (Holding Register)' },
  { value: 4, label: 'Method 4 - Okuma (Input Register)' },
  { value: 5, label: 'Method 5 - Yazma (Single Coil)' },
  { value: 6, label: 'Method 6 - Yazma (Single Register)' },
  { value: 15, label: 'Method 15 - Yazma (Multiple Coils)' },
  { value: 16, label: 'Method 16 - Yazma (Multiple Registers)' },
] as const;

/**
 * Device status constants
 */
export const DEVICE_STATUS = {
  ONLINE: 'ONLINE',
  OFFLINE: 'OFFLINE',
  PENDING: 'PENDING',
} as const;

/**
 * Time period options for analytics
 */
export const PERIOD_OPTIONS = [
  { value: 'hourly', label: 'Saatlik' },
  { value: 'daily', label: 'Günlük' },
  { value: 'weekly', label: 'Haftalık' },
  { value: 'monthly', label: 'Aylık' },
] as const;

/**
 * Metric type options for analytics
 */
export const METRIC_OPTIONS = [
  { value: '19l', label: '19L Sayaç' },
  { value: '5l', label: '5L Sayaç' },
  { value: 'total', label: 'Toplam' },
] as const;

/**
 * Pagination defaults
 */
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 20,
  MAX_PAGE_SIZE: 100,
} as const;

/**
 * WebSocket connection states
 */
export const WS_STATE = {
  CONNECTING: 0,
  OPEN: 1,
  CLOSING: 2,
  CLOSED: 3,
} as const;

/**
 * Refresh intervals (in milliseconds)
 */
export const REFRESH_INTERVALS = {
  DEVICES: 30000,      // 30 seconds
  ANALYTICS: 60000,    // 1 minute
  DASHBOARD: 30000,    // 30 seconds
  WEBSOCKET: 5000,     // 5 seconds (reconnect attempt)
} as const;
