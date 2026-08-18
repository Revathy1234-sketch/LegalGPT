import { apiClient } from './client';

export interface SearchResult {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  contract_id: string;
}

export const searchApi = {
  query: async (q: string): Promise<SearchResult[]> => {
    const response = await apiClient.get<SearchResult[]>('/api/v1/search/', { params: { q } });
    return response.data;
  },
};
