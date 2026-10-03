import { apiClient } from './client';

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  avatar_url?: string;
}

export interface UserUpdatePayload {
  first_name?: string;
  last_name?: string;
  email?: string;
}

export const usersApi = {
  getMe: async (): Promise<UserResponse> => {
    const response = await apiClient.get<UserResponse>('/api/v1/users/me');
    return response.data;
  },
  updateMe: async (data: UserUpdatePayload): Promise<UserResponse> => {
    const response = await apiClient.patch<UserResponse>('/api/v1/users/me', data);
    return response.data;
  },
  updateAvatar: async (file: File): Promise<UserResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<UserResponse>('/api/v1/users/me/avatar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};
