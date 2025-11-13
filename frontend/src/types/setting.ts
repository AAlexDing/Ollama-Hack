export enum SystemSettingKey {
  UPDATE_ENDPOINT_TASK_INTERVAL_HOURS = "update_endpoint_task_interval_hours",
  DISABLE_OLLAMA_API_AUTH = "disable_ollama_api_auth",
}

export interface SystemSettings {
  key: SystemSettingKey;
  value: string;
  created_at: string;
}
