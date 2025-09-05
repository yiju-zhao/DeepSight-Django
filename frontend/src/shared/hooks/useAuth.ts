import { useNavigate } from 'react-router-dom';
import { useCurrentUser, useLogout as useLogoutMutation } from '@/shared/queries/auth';
import type { User } from '@/shared/types';

// Hook return type
interface UseAuthReturn {
  isAuthenticated: boolean;
  user: User | null;
  isLoading: boolean;
  authChecked: boolean;
  handleLogout: () => Promise<void>;
}

/**
 * Custom hook for authentication management using React Query
 * Prevents redundant API calls through proper caching
 */
export const useAuth = (): UseAuthReturn => {
  const navigate = useNavigate();
  const { data: user, isLoading, isError, isFetched } = useCurrentUser();
  const logoutMutation = useLogoutMutation();

  const isAuthenticated = !!user && !isError;
  const authChecked = isFetched; // Use isFetched instead of custom state

  const handleLogout = async (): Promise<void> => {
    try {
      await logoutMutation.mutateAsync();
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error);
      // Even if logout fails, redirect to login page
      navigate('/login');
    }
  };

  return {
    isAuthenticated,
    user: user || null,
    isLoading,
    authChecked,
    handleLogout,
  };
};