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

export interface ChatHistoryMessage {
  role: string;
  content: string;
  created_at?: string;
  metadata?: Record<string, unknown> | null;
}

export interface EnterpriseChatResponse {
  status?: string;
  result?: ContractQuestionResponse;
}

export interface WorkspaceChatResponse {
  session_id: string;
  answer: string;
  created_at: string;
  error: boolean;
}

export interface WorkspaceSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface WorkspaceMessage {
  id: string;
  role: string;
  content: string;
  created_at: string;
  metadata?: Record<string, unknown> | null;
}

export const chatApi = {
  ask: async (contractId: string, question: string): Promise<ContractQuestionResponse> => {
    const payload: ContractQuestionRequest = { question };
    const response = await apiClient.post<EnterpriseChatResponse | ContractQuestionResponse>(`/api/v1/analysis/chat/${contractId}`, payload);

    // Extract from EnterpriseResponse format
    let result: ContractQuestionResponse;
    if (response.data && 'result' in response.data && (response.data as EnterpriseChatResponse).result) {
      result = (response.data as EnterpriseChatResponse).result as ContractQuestionResponse;
    } else {
      result = response.data as ContractQuestionResponse;
    }

    // Backend `citations` carry the actual PDF passages (content_preview);
    // normalize them into `sources` so the evidence panel can show the proof.
    const raw = result as unknown as {
      sources?: ContractQuestionSource[];
      citations?: Array<{ chunk_id?: string; parent_id?: string; content_preview?: string; relevance_score?: number }>;
    };
    if ((!raw.sources || raw.sources.length === 0) && raw.citations && raw.citations.length > 0) {
      raw.sources = raw.citations.map((c) => ({
        parent_id: c.parent_id || '',
        chunk_id: c.chunk_id || '',
        child_text: c.content_preview || '',
        parent_text: c.content_preview || '',
        relevance_score: c.relevance_score ?? 0,
      }));
    }
    return result;
  },
  
  getHistory: async (contractId: string): Promise<ChatHistoryMessage[]> => {
    const response = await apiClient.get<ChatHistoryMessage[]>(`/api/v1/analysis/chat/${contractId}`);
    return response.data;
  },

  // ---- AI Workspace (global) chat: every prompt + response is persisted ----
  workspaceAsk: async (
    message: string,
    sessionId?: string | null,
    contractId?: string | null,
  ): Promise<WorkspaceChatResponse> => {
    const payload: Record<string, unknown> = { message };
    if (sessionId) payload.session_id = sessionId;
    if (contractId) payload.contract_id = contractId;
    const response = await apiClient.post<WorkspaceChatResponse>('/api/v1/chat/workspace', payload);
    return response.data;
  },

  listWorkspaceSessions: async (): Promise<WorkspaceSession[]> => {
    const response = await apiClient.get<WorkspaceSession[]>('/api/v1/chat/workspace/sessions');
    return response.data;
  },

  getWorkspaceMessages: async (sessionId: string): Promise<WorkspaceMessage[]> => {
    const response = await apiClient.get<WorkspaceMessage[]>(`/api/v1/chat/workspace/sessions/${sessionId}`);
    return response.data;
  },
};
