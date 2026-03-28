export interface Reading {
  id: number;
  device_id: number;
  timestamp: string;
  counter_19l: number | null;
  counter_5l: number | null;
}

export interface ReadingDelta {
  timestamp: string;
  counter_19l: number;
  counter_5l: number;
  counter_total: number;
  delta_19l: number;
  delta_5l: number;
  delta_total: number;
}

export interface ReadingQueryParams {
  device_id?: number | number[];
  start_date?: string;
  end_date?: string;
  period?: 'hourly' | 'daily' | 'weekly' | 'monthly';
  limit?: number;
  offset?: number;
}

export interface ReadingResponse {
  data: Reading[];
  total: number;
  page: number;
  page_size: number;
}
