import { apiClient } from './client';

export interface HistoryItem {
  id: string;
  contract_id: string;
  contract_name: string;
  task_type: string;
  status: string;
  created_at: string;
  latency_ms: number | null;
}

export const historyApi = {
  getAll: async (): Promise<HistoryItem[]> => {
    const response = await apiClient.get<HistoryItem[]>('/api/v1/history/');
    return response.data;
  },
};
