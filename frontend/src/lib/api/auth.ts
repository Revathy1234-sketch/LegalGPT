import { apiClient } from './client';

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserCreate {
  email: string;
  password: string;
  full_name?: string;
}

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
}

export const authApi = {
  login: async (data: URLSearchParams): Promise<TokenResponse> => {
    // The backend expects application/x-www-form-urlencoded for OAuth2PasswordBearer
    const response = await apiClient.post<TokenResponse>('/api/v1/auth/login', data, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  },

  register: async (data: UserCreate): Promise<UserResponse> => {
    const response = await apiClient.post<UserResponse>('/api/v1/auth/register', data);
    return response.data;
  },
};
