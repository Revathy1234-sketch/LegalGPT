import { apiClient } from './client';

export interface ContractQuestionRequest {
  question: string;
}

export interface ContractQuestionSource {
  parent_id: string;
  chunk_id: string;
  child_text: string;
  parent_text: string;
  relevance_score: number;
}

export interface ContractQuestionResponse {
  answer: string;
  confidence: number;
  sources: ContractQuestionSource[];
}

export interface EnterpriseChatResponse {
  status?: string;
  result?: ContractQuestionResponse;
}

export const chatApi = {
  ask: async (contractId: string, question: string): Promise<ContractQuestionResponse> => {
    const payload: ContractQuestionRequest = { question };
    const response = await apiClient.post<EnterpriseChatResponse | ContractQuestionResponse>(`/api/v1/analysis/chat/${contractId}`, payload);

    // Extract from EnterpriseResponse format
    if (response.data && 'result' in response.data && (response.data as EnterpriseChatResponse).result) {
      return (response.data as EnterpriseChatResponse).result as ContractQuestionResponse;
    }
    return response.data as ContractQuestionResponse;
  },
  
  getHistory: async (contractId: string): Promise<any[]> => {
    const response = await apiClient.get<any[]>(`/api/v1/analysis/chat/${contractId}`);
    return response.data;
  }
};
