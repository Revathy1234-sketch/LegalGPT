import { apiClient } from './client';

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
}

export const usersApi = {
  getMe: async (): Promise<UserResponse> => {
    const response = await apiClient.get<UserResponse>('/api/v1/users/me');
    return response.data;
  },
};
