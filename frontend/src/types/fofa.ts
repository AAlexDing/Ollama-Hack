/**
 * FOFA扫描相关类型定义
 */

export type FofaScanStatus = "pending" | "running" | "completed" | "failed";

export interface FofaScanRequest {
  country?: string;
  custom_query?: string | null;
  auto_test?: boolean;
  test_delay_seconds?: number;
}

export interface FofaScanResponse {
  scan_id: number;
  status: string;
  query: string;
  country: string;
  total_found: number;
  total_created: number;
  message: string;
}

export interface FofaScanInfo {
  id: number;
  query: string;
  country: string;
  status: FofaScanStatus;
  total_found: number;
  total_created: number;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}

