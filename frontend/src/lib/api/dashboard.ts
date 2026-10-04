import { apiClient } from './client';

export interface DashboardStats {
  total_contracts: number;
  high_risk: number;
  pending_analysis: number;
  completed_analyses: number;
}

export interface RecentActivity {
  id: string;
  title: string;
  target: string;
  time: string;
  type: string;
}

export interface RecentContract {
  id: string;
  name: string;
  type: string;
  date: string;
  status: string;
  risk: string;
  lastAnalysis: string;
}

export interface RiskFinding {
  category?: string;
  description?: string;
  impact?: string;
  evidence?: string;
  page?: string;
  section?: string;
  source_text?: string;
  mitigation?: string;
  severity?: string;
}

export interface RiskDistribution {
  name: string;
  value: number;
  color: string;
  findings: RiskFinding[];
}

export interface DashboardData {
  stats: DashboardStats;
  recent_activity: RecentActivity[];
  recent_contracts: RecentContract[];
  risk_distribution: RiskDistribution[];
  contract_types?: { type: string; count: number }[];
  status_distribution?: { name: string; value: number; color: string }[];
  risk_radar?: { category: string; score: number }[];
  agent_usage?: { name: string; count: number }[];
}

export const dashboardApi = {
  getStats: async (): Promise<DashboardData> => {
    const response = await apiClient.get<DashboardData>('/api/v1/dashboard/stats');
    return response.data;
  },
  getAgentStatus: async (): Promise<Array<{name: string, status: string, executions: number}>> => {
    const response = await apiClient.get('/api/v1/dashboard/agent-status');
    return response.data;
  },
};
