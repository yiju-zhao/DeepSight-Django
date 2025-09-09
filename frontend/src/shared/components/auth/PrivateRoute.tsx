import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/shared/hooks/useAuth';
import { LoadingSpinner } from '@/shared/components/ui/LoadingSpinner';

interface PrivateRouteProps {
  children: React.ReactNode;
}

/**
 * PrivateRoute component that protects routes by checking authentication status
 * Redirects to login page if user is not authenticated
 */
export const PrivateRoute: React.FC<PrivateRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading, authChecked } = useAuth();
  const location = useLocation();

  // Show loading spinner while checking authentication
  if (isLoading || !authChecked) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  // If not authenticated, redirect to login page with the current location
  if (!isAuthenticated) {
    return (
      <Navigate 
        to="/login" 
        state={{ from: location.pathname }} 
        replace 
      />
    );
  }

  // If authenticated, render the protected component
  return <>{children}</>;
};

export default PrivateRoute;