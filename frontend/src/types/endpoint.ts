import {
  AIModelStatusEnum,
  EndpointStatusEnum,
  TaskStatusEnum,
} from "./common";

// 端点信息
export interface EndpointInfo {
  id?: number;
  url: string;
  name: string;
  created_at?: string;
}

// 端点性能信息
export interface EndpointPerformanceInfo {
  id?: number;
  status: EndpointStatusEnum;
  ollama_version?: string;
  created_at: string;
}

// AI模型摘要信息（用于列表显示）
export interface EndpointAIModelSummary {
  name: string;
  tag: string;
  status: string; // 模型状态：available, unavailable, missing, fake等
}

// 带 AI 模型数量的端点信息
export interface EndpointWithAIModelCount extends EndpointInfo {
  recent_performances: EndpointPerformanceInfo[];
  total_ai_model_count: number;
  avaliable_ai_model_count: number;
  task_status?: TaskStatusEnum;
  max_tps?: number | null; // 最大TPS（所有可用模型的TPS最大值）
  tps_updated_at?: string | null; // TPS更新时间（最新性能测试时间）
  ai_models?: EndpointAIModelSummary[]; // AI模型列表（用于显示）
}

// 端点 AI 模型信息
export interface EndpointAIModelInfo {
  id: number;
  name: string;
  tag: string;
  created_at: string;
  status: AIModelStatusEnum;
  token_per_second?: number;
  max_connection_time?: number;
}

// 带 AI 模型列表的端点信息
export interface EndpointWithAIModels extends EndpointInfo {
  recent_performances: EndpointPerformanceInfo[];
  ai_models: {
    items: EndpointAIModelInfo[];
    total?: number;
    page?: number;
    size?: number;
    pages?: number;
  };
}

// 端点创建请求
export interface EndpointCreate {
  url: string;
  name?: string;
}

// 端点更新请求
export interface EndpointUpdate {
  name?: string;
}

// 批量创建端点请求
export interface EndpointBatchCreate {
  endpoints: EndpointCreate[];
}

// 批量操作端点请求
export interface EndpointBatchOperation {
  endpoint_ids: number[]; // 要操作的节点ID列表
}

// 批量操作结果响应
export interface BatchOperationResult {
  success_count: number; // 成功操作的节点数量
  failed_count: number; // 失败的节点数量
  failed_ids: {
    // 失败的节点ID及原因
    [key: string]: string;
  };
}

// 端点任务信息
export interface EndpointTaskInfo {
  id: number;
  endpoint_id: number;
  status: TaskStatusEnum;
  scheduled_at: string;
  last_tried?: string;
  created_at: string;
}
