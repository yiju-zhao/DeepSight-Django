/**
 * Dashboard header component
 * Focused component for the dashboard title and main header
 */

import React from 'react';

interface DashboardHeaderProps {
  title?: string;
  subtitle?: string;
  className?: string;
}

const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  title = 'DeepSight',
  subtitle,
  className = '',
}) => {
  return (
    <div className={`mb-8 ${className}`}>
      <h1 className="text-4xl font-bold">{title}</h1>
      {subtitle && (
        <p className="text-lg text-gray-600 mt-2">{subtitle}</p>
      )}
    </div>
  );
};

export default DashboardHeader;