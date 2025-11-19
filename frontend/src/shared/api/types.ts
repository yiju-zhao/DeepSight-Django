/**
 * Core API types and interfaces
 */

export interface ApiResponse<T> {
  data: T;
  meta?: {
    pagination?: PaginationMeta;
    filters?: FiltersMeta;
  };
}

export interface PaginatedResponse<T> {
  count: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  next: string | null;
  previous: string | null;
  results: T[];
  stats?: {
    [key: string]: any;
  };
}

export interface PaginationMeta {
  count: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  next: string | null;
  previous: string | null;
}

export interface FiltersMeta {
  search?: string;
  ordering?: string;
  [key: string]: any;
}

export interface PaginationParams {
  page?: number;
  pageSize?: number;
  search?: string;
  ordering?: string;
}

export interface RequestConfig extends RequestInit {
  params?: Record<string, any>;
  timeout?: number;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public response?: Response
  ) {
    super(message);
    this.name = 'ApiError';
  }
}