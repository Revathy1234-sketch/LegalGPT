import { apiClient } from './client';

export interface ContractResponse {
  id: string;
  file_name: string;
  storage_url: string | null;
  status: string;
  summary: string | null;
  uploaded_by: string;
  created_at: string;
  clauses?: Record<string, unknown>[];
  risk_analysis?: {
    overall_score: number;
    [key: string]: unknown;
  };
}

export const contractsApi = {
  getAll: async (): Promise<ContractResponse[]> => {
    const response = await apiClient.get<ContractResponse[]>('/api/v1/contracts/');
    return response.data;
  },

  getById: async (id: string): Promise<ContractResponse> => {
    const response = await apiClient.get<ContractResponse>(`/api/v1/contracts/${id}`);
    return response.data;
  },

  upload: async (file: File): Promise<ContractResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<ContractResponse>('/api/v1/contracts/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};
