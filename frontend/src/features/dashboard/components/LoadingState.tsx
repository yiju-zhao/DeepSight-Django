/**
 * Loading state component for the dashboard
 * Provides consistent loading UI
 */

import React from 'react';

interface LoadingStateProps {
  message?: string;
  className?: string;
}

const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading dashboard…',
  className = '',
}) => {
  return (
    <div className={`flex items-center justify-center h-screen ${className}`}>
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-4"></div>
        <span className="text-gray-500">{message}</span>
      </div>
    </div>
  );
};

export default LoadingState;