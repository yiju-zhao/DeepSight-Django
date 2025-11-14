import React from 'react';

interface ChartCardProps {
  title: string;
  children: React.ReactNode;
  isLoading?: boolean;
  height?: string;
}

/**
 * HUAWEI-style chart card component with elevation shadows and smooth transitions
 */
export const ChartCard = ({
  title,
  children,
  isLoading,
  height = "h-80"
}: ChartCardProps) => {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-[rgba(0,0,0,0.08)_0px_8px_12px] p-6">
        <div className="h-5 bg-[#F5F5F5] rounded animate-pulse w-48 mb-6" />
        <div className={`${height} bg-[#F5F5F5] rounded animate-pulse`} />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-[rgba(0,0,0,0.08)_0px_8px_12px] hover:shadow-[rgba(0,0,0,0.12)_0px_12px_20px] transition-shadow duration-300 p-6">
      {title && (
        <h3 className="text-xl font-bold text-[#1E1E1E] mb-6">{title}</h3>
      )}
      <div className={height}>
        {children}
      </div>
    </div>
  );
};
