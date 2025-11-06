/**
 * 订阅API服务
 */
import type {
  PullSubscriptionResponse,
  SubscriptionInfo,
  SubscriptionProgressResponse,
  SubscriptionRequest,
  SubscriptionResponse,
  UpdateSubscriptionRequest,
} from "../types/subscription";

import { apiClient } from "./client";

const subscriptionApi = {
  /**
   * 创建订阅
   */
  async createSubscription(
    data: SubscriptionRequest
  ): Promise<SubscriptionResponse> {
    return await apiClient.post<SubscriptionResponse>(
      "/api/v2/subscription/",
      data
    );
  },

  /**
   * 获取订阅信息
   */
  async getSubscription(subscriptionId: number): Promise<SubscriptionInfo> {
    return await apiClient.get<SubscriptionInfo>(
      `/api/v2/subscription/${subscriptionId}`
    );
  },

  /**
   * 获取订阅列表
   */
  async getSubscriptionList(params?: {
    limit?: number;
    offset?: number;
  }): Promise<SubscriptionInfo[]> {
    return await apiClient.get<SubscriptionInfo[]>("/api/v2/subscription/", {
      params,
    });
  },

  /**
   * 手动拉取订阅
   */
  async pullSubscription(
    subscriptionId: number,
    testDelaySeconds: number = 5
  ): Promise<PullSubscriptionResponse> {
    return await apiClient.post<PullSubscriptionResponse>(
      `/api/v2/subscription/${subscriptionId}/pull`,
      null,
      { params: { test_delay_seconds: testDelaySeconds } }
    );
  },

  /**
   * 更新订阅
   */
  async updateSubscription(
    subscriptionId: number,
    data: UpdateSubscriptionRequest
  ): Promise<SubscriptionInfo> {
    return await apiClient.patch<SubscriptionInfo>(
      `/api/v2/subscription/${subscriptionId}`,
      data
    );
  },

  /**
   * 获取订阅进度
   */
  async getProgress(
    subscriptionId: number
  ): Promise<SubscriptionProgressResponse> {
    return await apiClient.get<SubscriptionProgressResponse>(
      `/api/v2/subscription/${subscriptionId}/progress`
    );
  },
};

export default subscriptionApi;
