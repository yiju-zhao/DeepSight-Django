/**
 * Empty state component for the dashboard
 * Displays when there's no content to show
 */

import React from 'react';

interface EmptyStateProps {
  icon?: string;
  title?: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

const EmptyState: React.FC<EmptyStateProps> = ({
  icon = '📊',
  title = 'No content yet',
  description = 'Get started by creating your first research report or podcast.',
  action,
  className = '',
}) => {
  return (
    <div className={`text-center py-10 ${className}`}>
      <div
        className="h-12 w-12 rounded-full border border-dashed border-gray-300 mx-auto mb-4 flex items-center justify-center text-gray-400"
        role="img"
        aria-label="Empty state icon"
      >
        <span className="text-xl leading-none">{icon}</span>
      </div>
      <h3 className="text-base font-medium text-gray-900 mb-1">{title}</h3>
      <p className="text-xs text-gray-500 mb-5 max-w-md mx-auto">
        {description}
      </p>
      {action && (
        <div className="flex justify-center">
          {action}
        </div>
      )}
    </div>
  );
};

export default EmptyState;
