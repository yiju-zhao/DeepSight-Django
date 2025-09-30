/**
 * React Query hooks for authentication and user data
 * Prevents redundant API calls by using proper caching
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { config } from "@/config";

// Backend User response type
interface BackendUser {
  id: string;
  username: string;
  email: string;
}

// Frontend User type (for compatibility)
interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  role: string;
  createdAt: string;
  updatedAt: string;
}

// Query Keys Factory
export const authQueries = {
  all: ['auth'] as const,
  user: () => [...authQueries.all, 'user'] as const,
  csrf: () => [...authQueries.all, 'csrf'] as const,
} as const;

// Helper function to get CSRF token from cookies
const getCookie = (name: string) => {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  const value = match?.[2];
  return value ? decodeURIComponent(value) : null;
};

// Helper function to transform backend user to frontend user format
const transformUser = (backendUser: BackendUser): User => ({
  id: backendUser.id,
  email: backendUser.email,
  name: backendUser.username, // Map username to name
  role: 'user', // Default role
  createdAt: new Date().toISOString(), // Default value
  updatedAt: new Date().toISOString(), // Default value
});

// API Functions
const fetchCurrentUser = async (): Promise<User> => {
  const response = await fetch(`${config.API_BASE_URL}/users/me/`, {
    method: 'GET',
    credentials: 'include',
  });
  
  if (!response.ok) {
    throw new Error('Not authenticated');
  }
  
  const backendUser: BackendUser = await response.json();
  return transformUser(backendUser);
};

const fetchCsrfToken = async (): Promise<{ csrfToken: string }> => {
  const response = await fetch(`${config.API_BASE_URL}/users/csrf/`, {
    method: 'GET',
    credentials: 'include',
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch CSRF token');
  }
  
  return response.json();
};

const loginUser = async (credentials: { username: string; password: string }): Promise<User> => {
  const response = await fetch(`${config.API_BASE_URL}/users/login/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken') || '',
    },
    credentials: 'include',
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Login failed');
  }

  const backendUser: BackendUser = await response.json();
  return transformUser(backendUser);
};

const signupUser = async (userData: { username: string; email: string; password: string; password_confirm: string }): Promise<User> => {
  const response = await fetch(`${config.API_BASE_URL}/users/signup/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken') || '',
    },
    credentials: 'include',
    body: JSON.stringify(userData),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Signup failed');
  }

  const backendUser: BackendUser = await response.json();
  return transformUser(backendUser);
};

const logoutUser = async (): Promise<void> => {
  const response = await fetch(`${config.API_BASE_URL}/users/logout/`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'X-CSRFToken': getCookie('csrftoken') || '',
    },
  });

  if (!response.ok) {
    throw new Error('Logout failed');
  }
};

// React Query Hooks
export const useCurrentUser = () => {
  return useQuery({
    queryKey: authQueries.user(),
    queryFn: fetchCurrentUser,
    staleTime: 10 * 60 * 1000, // 10 minutes - user data doesn't change often
    gcTime: 15 * 60 * 1000, // 15 minutes cache time
    retry: false, // Don't retry auth failures
    refetchOnWindowFocus: false, // Don't refetch on window focus
  });
};

export const useCsrfToken = () => {
  return useQuery({
    queryKey: authQueries.csrf(),
    queryFn: fetchCsrfToken,
    staleTime: 30 * 60 * 1000, // 30 minutes - CSRF tokens are long-lived
    gcTime: 60 * 60 * 1000, // 1 hour cache time
  });
};

export const useLogin = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: loginUser,
    onSuccess: (user) => {
      // Update the user cache immediately
      queryClient.setQueryData(authQueries.user(), user);
      
      // Invalidate and refetch any notebook data after login
      queryClient.invalidateQueries({ queryKey: ['notebooks'] });
    },
  });
};

export const useSignup = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: signupUser,
    onSuccess: (user) => {
      // Update the user cache immediately
      queryClient.setQueryData(authQueries.user(), user);
    },
  });
};

export const useLogout = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: logoutUser,
    onSuccess: () => {
      // Clear ALL cached data on logout for security
      queryClient.clear();
    },
    onError: () => {
      // Even if logout fails on server, clear local cache
      queryClient.clear();
    },
  });
};

// Convenience hook that combines auth state
export const useAuth = () => {
  const { data: user, isLoading, error, isError } = useCurrentUser();
  
  return {
    user,
    isAuthenticated: !!user && !isError,
    isLoading,
    error,
    isError,
  };
};