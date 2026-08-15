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

export const chatApi = {
  ask: async (contractId: string, question: string): Promise<ContractQuestionResponse> => {
    const payload: ContractQuestionRequest = { question };
    const response = await apiClient.post<ContractQuestionResponse>(`/api/v1/contracts/${contractId}/ask`, payload);
    return response.data;
  },
};
