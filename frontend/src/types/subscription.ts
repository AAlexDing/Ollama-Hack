/**
 * 订阅相关类型定义
 */
export interface SubscriptionRequest {
  url: string;
  pull_interval: number;
}

export interface SubscriptionResponse {
  subscription_id: number;
  url: string;
  pull_interval: number;
  message: string;
}

export interface SubscriptionInfo {
  id: number;
  url: string;
  pull_interval: number;
  last_pull_at: string | null;
  last_pull_count: number;
  total_pulls: number;
  total_created: number;
  is_enabled: boolean;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface PullSubscriptionResponse {
  subscription_id: number;
  pull_count: number;
  created_count: number;
  message: string;
}

export interface UpdateSubscriptionRequest {
  pull_interval?: number;
  is_enabled?: boolean;
}

