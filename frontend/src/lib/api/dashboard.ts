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

export interface RiskDistribution {
  name: string;
  value: number;
  color: string;
}

export interface DashboardData {
  stats: DashboardStats;
  recent_activity: RecentActivity[];
  recent_contracts: RecentContract[];
  risk_distribution: RiskDistribution[];
}

export const dashboardApi = {
  getStats: async (): Promise<DashboardData> => {
    const response = await apiClient.get<DashboardData>('/api/v1/dashboard/stats');
    return response.data;
  },
};
