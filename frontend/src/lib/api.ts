import { AuthStorage } from './auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * API endpoint paths
 */
export const endpoints = {
  // Auth
  login: '/api/v1/auth/login',
  logout: '/api/v1/auth/logout',
  me: '/api/v1/auth/me',
  refresh: '/api/v1/auth/refresh',

  // Devices
  devices: '/api/v1/devices',
  device: (id: number) => `/api/v1/devices/${id}`,
  deviceSummary: (id: number) => `/api/v1/devices/${id}/summary`,

  // Readings
  readings: '/api/v1/readings',
  deviceReadings: (id: number) => `/api/v1/readings/device/${id}`,

  // Analytics
  analyticsRevenue: '/api/v1/analytics/revenue',
  analyticsComparison: '/api/v1/analytics/comparison',
  analyticsTrend: '/api/v1/analytics/trend',
  analyticsPeakHours: '/api/v1/analytics/peak-hours',
  analyticsDowntime: '/api/v1/analytics/downtime',

  // Dashboard
  dashboardOverview: '/api/v1/dashboard/overview',
  dashboardRealtime: '/api/v1/dashboard/realtime',
  dashboardAlerts: '/api/v1/dashboard/alerts',

  // Monitoring
  monitoringHealth: '/health',
  monitoringMetrics: '/api/v1/monitoring/metrics',

  // MQTT Logs
  mqttLogs: '/api/v1/mqtt-logs',
};

/**
 * Custom API error class
 */
class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Build query string from params object
 */
function buildQueryString(params?: Record<string, string | number | undefined>): string {
  if (!params) return '';
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.append(key, String(value));
    }
  });
  const qs = searchParams.toString();
  return qs ? `?${qs}` : '';
}

/**
 * Get authorization headers
 */
function getAuthHeaders(): Record<string, string> {
  const token = AuthStorage.getAccessToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

/**
 * Handle API response
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    if (response.status === 401) {
      // Token expired or invalid - clear auth and redirect
      AuthStorage.clearAll();
      if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    let errorData: unknown;
    try {
      errorData = await response.json();
    } catch {
      errorData = { detail: response.statusText };
    }
    const message =
      (errorData as { detail?: string })?.detail ||
      `HTTP Error ${response.status}`;
    throw new ApiError(message, response.status, errorData);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

/**
 * API client with typed request methods
 */
export const api = {
  /**
   * GET request
   */
  async get<T>(url: string, params?: Record<string, string | number | undefined>): Promise<T> {
    const queryString = buildQueryString(params);
    const response = await fetch(`${API_BASE_URL}${url}${queryString}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
    });
    return handleResponse<T>(response);
  },

  /**
   * POST request
   */
  async post<T>(url: string, data?: unknown): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${url}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: data ? JSON.stringify(data) : undefined,
    });
    return handleResponse<T>(response);
  },

  /**
   * PUT request
   */
  async put<T>(url: string, data?: unknown): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${url}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: data ? JSON.stringify(data) : undefined,
    });
    return handleResponse<T>(response);
  },

  /**
   * PATCH request
   */
  async patch<T>(url: string, data?: unknown): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${url}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: data ? JSON.stringify(data) : undefined,
    });
    return handleResponse<T>(response);
  },

  /**
   * DELETE request
   */
  async delete<T = void>(url: string): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${url}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
    });
    return handleResponse<T>(response);
  },
};
