/**
 * Reports section component for the dashboard
 * Handles display of trending reports
 * Optimized with React.memo to prevent unnecessary re-renders
 */

import React, { useMemo } from 'react';
import ReportListItem from '@/features/report/components/ReportListItem';
import { Report } from '../queries';

interface ReportsSectionProps {
  reports: Report[];
  onReportSelect: (report: Report) => void;
  loading?: boolean;
  className?: string;
}

const ReportsSection: React.FC<ReportsSectionProps> = React.memo(({
  reports,
  onReportSelect,
  loading = false,
  className = '',
}) => {
  // Memoize loading skeleton to prevent re-creation
  const loadingSkeleton = useMemo(() => (
    <div className={`mb-8 ${className}`}>
      <div className="bg-white/80 backdrop-blur-sm rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="animate-pulse">
              <div className="h-20 bg-gray-200 rounded-lg"></div>
            </div>
          ))}
        </div>
      </div>
    </div>
  ), [className]);

  if (loading) {
    return loadingSkeleton;
  }

  if (reports.length === 0) {
    return (
      <div className={`mb-8 ${className}`}>
        <div className="bg-white/80 backdrop-blur-sm rounded-xl border border-gray-200 shadow-sm p-6">
          <div className="text-center py-6">
            <div className="h-10 w-10 rounded-full border border-dashed border-gray-300 mx-auto mb-3 flex items-center justify-center text-gray-400">📊</div>
            <h3 className="text-sm font-medium text-gray-900 mb-1">No trending reports</h3>
            <p className="text-xs text-gray-500">Check back later for trending research.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`mb-8 ${className}`}>
      <div className="bg-white/80 backdrop-blur-sm rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="mb-4">
          <h2 className="text-base font-semibold text-gray-900">Trending Reports</h2>
          <p className="text-xs text-gray-500">Latest AI-generated research summaries</p>
        </div>
        <div className="space-y-3">
          {reports.map((report) => (
            <ReportListItem
              key={report.id}
              report={report}
              onSelect={onReportSelect}
            />
          ))}
        </div>
      </div>
    </div>
  );
});

ReportsSection.displayName = 'ReportsSection';

export default ReportsSection;
