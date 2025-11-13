import apiClient, { buildQueryString } from "./client";

import {
  BatchOperationResult,
  EndpointBatchCreate,
  EndpointBatchOperation,
  EndpointCreate,
  EndpointInfo,
  EndpointTaskInfo,
  EndpointUpdate,
  EndpointWithAIModelCount,
  EndpointWithAIModels,
  PageResponse,
  QueryParams,
} from "@/types";

export const endpointApi = {
  // 获取所有端点（带最近性能测试和 AI 模型数量）
  getEndpoints: (params: QueryParams = {}) => {
    const queryString = buildQueryString({
      page: params.page || 1,
      size: params.size || 50,
      search: params.search,
      order_by: params.order_by,
      order: params.order,
      status: params.status,
    });

    return apiClient.get<PageResponse<EndpointWithAIModelCount>>(
      `/api/v2/endpoint/${queryString}`,
    );
  },

  // 创建新端点
  createEndpoint: (data: EndpointCreate) => {
    return apiClient.post<EndpointInfo>("/api/v2/endpoint/", data);
  },

  // 获取单个端点详情（包含 AI 模型）
  getEndpointById: (
    endpointId: number,
    page: number = 1,
    size: number = 50,
  ) => {
    return apiClient.get<EndpointWithAIModels>(
      `/api/v2/endpoint/${endpointId}?page=${page}&size=${size}`,
    );
  },

  // 更新端点
  updateEndpoint: (endpointId: number, data: EndpointUpdate) => {
    return apiClient.patch<EndpointInfo>(
      `/api/v2/endpoint/${endpointId}`,
      data,
    );
  },

  // 删除端点
  deleteEndpoint: (endpointId: number) => {
    return apiClient.delete<void>(`/api/v2/endpoint/${endpointId}`);
  },

  // 批量创建端点
  batchCreateEndpoints: (data: EndpointBatchCreate) => {
    return apiClient.post<EndpointInfo[]>("/api/v2/endpoint/batch", data);
  },

  // 批量测试端点
  batchTestEndpoints: (data: EndpointBatchOperation) => {
    return apiClient.post<BatchOperationResult>(
      "/api/v2/endpoint/batch-test",
      data,
    );
  },

  // 测试所有端点
  testAllEndpoints: () => {
    return apiClient.post<BatchOperationResult>(
      "/api/v2/endpoint/batch-test/all",
    );
  },

  // 批量删除端点
  batchDeleteEndpoints: (data: EndpointBatchOperation) => {
    return apiClient.delete<BatchOperationResult>("/api/v2/endpoint/batch", {
      data,
    });
  },

  // 手动触发端点测试
  triggerEndpointTest: (endpointId: number) => {
    return apiClient.post<void>(`/api/v2/endpoint/${endpointId}/test`);
  },

  // 获取端点测试结果
  getEndpointTask: (endpointId: number) => {
    return apiClient.get<EndpointTaskInfo>(
      `/api/v2/endpoint/${endpointId}/task`,
    );
  },
};

export default endpointApi;
