/**
 * FOFA扫描API服务
 */
import type {
  FofaScanInfo,
  FofaScanRequest,
  FofaScanResponse,
} from "../types/fofa";

import { apiClient } from "./client";

const fofaApi = {
  /**
   * 启动FOFA扫描
   */
  async startScan(data: FofaScanRequest): Promise<FofaScanResponse> {
    return await apiClient.post<FofaScanResponse>("/api/v2/fofa/scan", data);
  },

  /**
   * 获取扫描结果
   */
  async getScanResult(scanId: number): Promise<FofaScanInfo> {
    return await apiClient.get<FofaScanInfo>(`/api/v2/fofa/scan/${scanId}`);
  },

  /**
   * 获取扫描历史
   */
  async getScanHistory(params?: {
    limit?: number;
    offset?: number;
  }): Promise<FofaScanInfo[]> {
    return await apiClient.get<FofaScanInfo[]>("/api/v2/fofa/scans", {
      params,
    });
  },
};

export default fofaApi;
