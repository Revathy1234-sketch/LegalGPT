import { apiClient } from './client';

export interface SearchResultItem {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  contract_id: string;
  link?: string;
}

export interface SearchResultGroup {
  group: string;
  items: SearchResultItem[];
}

export const searchApi = {
  query: async (q: string): Promise<SearchResultGroup[]> => {
    const response = await apiClient.get<SearchResultGroup[]>('/api/v1/search/', { params: { q } });
    return response.data;
  },
};
