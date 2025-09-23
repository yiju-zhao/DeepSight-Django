import React from 'react';

interface ChartCardProps {
  title: string;
  children: React.ReactNode;
  isLoading?: boolean;
  height?: string;
}

export const ChartCard = ({
  title,
  children,
  isLoading,
  height = "h-80"
}: ChartCardProps) => {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="h-5 bg-gray-200 rounded animate-pulse w-48 mb-4" />
        <div className={`${height} bg-gray-200 rounded animate-pulse`} />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      <div className={height}>
        {children}
      </div>
    </div>
  );
};
