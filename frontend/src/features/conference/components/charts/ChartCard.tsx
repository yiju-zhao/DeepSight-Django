import React from 'react';

interface ChartCardProps {
  title: string;
  children: React.ReactNode;
  isLoading?: boolean;
  height?: string;
  action?: React.ReactNode;
}

/**
 * HUAWEI-style chart card component
 * - Clean white background
 * - Minimalist shadow
 * - Sharp header
 */
export const ChartCard = ({
  title,
  children,
  isLoading,
  height = "h-80",
  action
}: ChartCardProps) => {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-[0px_2px_6px_rgba(0,0,0,0.06)] p-6 border border-[#E3E3E3]">
        <div className="h-5 bg-[#F5F5F5] rounded animate-pulse w-48 mb-6" />
        <div className={`${height} bg-[#F5F5F5] rounded animate-pulse`} />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-[rgba(0,0,0,0.08)_0px_8px_12px] p-6 border border-[#E3E3E3] h-full flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-bold text-[#1E1E1E] tracking-tight">{title}</h3>
        {action && action}
      </div>
      <div className={`${height} flex-grow`}>
        {children}
      </div>
    </div>
  );
};
