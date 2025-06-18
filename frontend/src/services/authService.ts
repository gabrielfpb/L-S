import apiClient from './api'; // Your main axios client
import { AxiosError } from 'axios';
import { User } from '../contexts/AuthContext'; // Import User type from AuthContext

// Define Token types matching backend
interface TokenResponse {
    access_token: string;
    token_type: string;
}

// Define UserCreateData matching backend user_schemas.UserCreate
export interface UserCreateData {
    email: string;
    username: string;
    password: string;
    full_name?: string | null;
}

// Define UserCreateResponse matching backend user_schemas.UserCreateResponse
// This is often similar to User, but can differ (e.g. no password, includes created_at)
export interface UserCreateResponse extends User {
    // Add any fields specific to create response if different from User, e.g. created_at
    // For now, assuming User from AuthContext is sufficient
}


export const loginUser = async (credentials: any): Promise<{ token: string, user: User }> => {
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    try {
        const tokenData = (await apiClient.post<TokenResponse>('/auth/token', formData, {
             headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        })).data;

        // After getting token, fetch user details from /users/me
        // apiClient's interceptor should automatically add the token for this request if login was successful
        // and token was stored by login function in AuthContext (or here before calling AuthContext.login)
        // However, to be explicit and ensure the *new* token is used:
        const userResponse = (await apiClient.get<User>('/auth/users/me', {
            headers: { Authorization: `Bearer ${tokenData.access_token}` }
        })).data;

        return { token: tokenData.access_token, user: userResponse };
    } catch (error) {
        const axiosError = error as AxiosError;
        if (axiosError.response && axiosError.response.data) {
            throw new Error( (axiosError.response.data as any)?.detail || 'Login failed');
        }
        throw new Error('Login failed due to network or unknown error');
    }
};

export const registerUser = async (userData: UserCreateData): Promise<UserCreateResponse> => {
    try {
        const response = await apiClient.post<UserCreateResponse>('/auth/users/register', userData);
        return response.data;
    } catch (error) {
        const axiosError = error as AxiosError;
        if (axiosError.response && axiosError.response.data) {
             throw new Error( (axiosError.response.data as any)?.detail || 'Registration failed');
        }
        throw new Error('Registration failed due to network or unknown error');
    }
};

export const fetchCurrentUser = async (token: string): Promise<User> => {
    try {
        const response = await apiClient.get<User>('/auth/users/me', {
            headers: { Authorization: `Bearer ${token}` } // Pass token explicitly for this call
        });
        return response.data;
    } catch (error) {
        const axiosError = error as AxiosError;
        if (axiosError.response && axiosError.response.status === 401) {
            throw new Error('Session expired or token invalid.');
        }
        // Log detailed error for debugging if possible
        // console.error("fetchCurrentUser error:", axiosError.response?.data || axiosError.message);
        throw new Error('Failed to fetch current user details.');
    }
};
