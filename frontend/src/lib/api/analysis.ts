import { apiClient } from './client';
import { ContractResponse } from './contracts';

export interface ClauseExtractionItem {
  title: string;
  category: string;
  content: string;
  confidence_score: number;
}

export interface ClauseExtractionResponse {
  clauses: ClauseExtractionItem[];
}

export interface ComplianceIssue {
  framework: string;
  clause_type: string;
  status: string;
  gap_analysis: string | null;
}

export interface ComplianceResponse {
  compliant: boolean;
  issues: ComplianceIssue[];
  recommendations: string[];
}

export interface RiskMatrixItem {
  severity?: string;
  risk_level?: string;
  overall_score?: number;
  source?: string;
  issue?: string;
  description?: string;
  title?: string;
  impact?: string;
  business_impact?: string;
  mitigation?: string;
  suggestion?: string;
  [key: string]: unknown;
}

export interface RiskAnalysisResponse {
  overall_score: number;
  id: string;
  contract_id: string;
  evaluated_at: string;
  mitigation_plan: string | null;
  risk_matrix: RiskMatrixItem[] | null;
}

export interface NegotiationSuggestion {
  clause?: string;
  title?: string;
  problem?: string;
  issue?: string;
  impact?: string;
  business_impact?: string;
  wording?: string;
  suggested_redline?: string;
  priority?: string;
  risk_level?: string;
  confidence?: string;
  [key: string]: unknown;
}

export interface NegotiationAnalysisResponse {
  clauses?: Record<string, unknown>[];
  risk_matrix?: Record<string, unknown>[];
  compliance_report?: Record<string, unknown>[];
  negotiation_suggestions: NegotiationSuggestion[];
}

export interface CompareRequest {
  contract_a_id: string;
  contract_b_id: string;
}

export interface CompareResponse {
  similarities: string[];
  differences: string[];
  missing_clauses: string[];
  risk_differences: string[];
  summary: string;
}

export interface KnowledgeGraphEntity {
  id: string;
  type: string;
  name?: string;
  label?: string;
  description?: string;
  [key: string]: unknown;
}

export interface KnowledgeGraphRelationship {
  source: string;
  target: string;
  type?: string;
  relationship?: string;
  [key: string]: unknown;
}

export interface KnowledgeGraphResponse {
  success: boolean;
  result: {
    entities: KnowledgeGraphEntity[];
    relationships: KnowledgeGraphRelationship[];
  };
}

export interface StoredAgentEntry {
  has_result: boolean;
  result: Record<string, unknown> | null;
  executions: number;
  executed_at: string | null;
}

export interface StoredResultsResponse {
  contract_id: string;
  file_name: string;
  uploaded_at: string;
  summary_text: string | null;
  risk_score: number | null;
  results: Record<string, StoredAgentEntry>;
}

export const analysisApi = {
  /** Stored (already-executed) agent outputs — no LLM call, no re-run. */
  getStored: async (contractId: string): Promise<StoredResultsResponse> => {
    const response = await apiClient.get<StoredResultsResponse>(`/api/v1/analysis/stored/${contractId}`);
    return response.data;
  },

  summarize: async (contractId: string): Promise<ContractResponse> => {
    const response = await apiClient.post<ContractResponse>(`/api/v1/analysis/summarize/${contractId}`);
    return response.data;
  },

  clauses: async (contractId: string): Promise<ClauseExtractionResponse> => {
    const response = await apiClient.post<ClauseExtractionResponse>(`/api/v1/analysis/clauses/${contractId}`);
    return response.data;
  },

  risk: async (contractId: string): Promise<RiskAnalysisResponse> => {
    const response = await apiClient.post<RiskAnalysisResponse>(`/api/v1/analysis/risk/${contractId}`);
    return response.data;
  },

  compliance: async (contractId: string): Promise<ComplianceResponse> => {
    const response = await apiClient.post<ComplianceResponse>(`/api/v1/analysis/compliance/${contractId}`);
    return response.data;
  },

  negotiation: async (contractId: string): Promise<NegotiationAnalysisResponse> => {
    const response = await apiClient.post<NegotiationAnalysisResponse>(`/api/v1/analysis/negotiation/${contractId}`);
    return response.data;
  },

  compare: async (payload: CompareRequest): Promise<CompareResponse> => {
    const response = await apiClient.post<CompareResponse>('/api/v1/analysis/compare', payload);
    return response.data;
  },

  knowledgeGraph: async (contractId: string): Promise<KnowledgeGraphResponse> => {
    const response = await apiClient.post<KnowledgeGraphResponse>(`/api/v1/analysis/knowledge-graph/${contractId}`);
    return response.data;
  },
};
