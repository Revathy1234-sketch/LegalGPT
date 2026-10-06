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

export interface ContractStatusResponse {
  contract_id: string;
  processing: boolean;
  agents: {
    summary: string;
    clause: string;
    risk: string;
    compliance: string;
    negotiation: string;
    knowledge_graph: string;
    [key: string]: string;
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

  getStatus: async (id: string): Promise<ContractStatusResponse> => {
    const response = await apiClient.get<ContractStatusResponse>(`/api/v1/contracts/${id}/status`);
    return response.data;
  },

  upload: async (file: File): Promise<ContractResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<ContractResponse>(
      '/api/v1/contracts/upload',
      formData,
      {
        transformRequest: [
          function (data, headers) {
            // Delete the default application/json header to let the browser automatically
            // set multipart/form-data with the correct generated boundary.
            delete headers['Content-Type'];
            return data;
          },
        ],
      }
    );
    return response.data;
  },

  deleteContract: async (id: string): Promise<{ message: string; contract_id: string }> => {
    const response = await apiClient.delete<{ message: string; contract_id: string }>(`/api/v1/contracts/${id}`);
    return response.data;
  },
};
