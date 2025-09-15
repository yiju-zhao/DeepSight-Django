/**
 * Reports section component for the dashboard
 * Handles display of trending reports
 */

import React from 'react';
import ReportListItem from '@/features/report/components/ReportListItem';
import { Report } from '../hooks/useDashboardData';

interface ReportsSectionProps {
  reports: Report[];
  onReportSelect: (report: Report) => void;
  loading?: boolean;
  className?: string;
}

const ReportsSection: React.FC<ReportsSectionProps> = ({
  reports,
  onReportSelect,
  loading = false,
  className = '',
}) => {
  if (loading) {
    return (
      <div className={`mb-8 ${className}`}>
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="animate-pulse">
              <div className="h-24 bg-gray-200 rounded-lg"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (reports.length === 0) {
    return (
      <div className={`mb-8 ${className}`}>
        <div className="text-center py-8">
          <div className="text-gray-400 text-4xl mb-2">📊</div>
          <h3 className="text-lg font-medium text-gray-900 mb-1">No trending reports</h3>
          <p className="text-sm text-gray-500">
            Check back later for trending research reports.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`mb-8 ${className}`}>
      <h2 className="text-2xl font-semibold mb-4 text-gray-900">Trending Reports</h2>
      <div className="space-y-4">
        {reports.map((report) => (
          <ReportListItem
            key={report.id}
            report={report}
            onSelect={onReportSelect}
          />
        ))}
      </div>
    </div>
  );
};

export default ReportsSection;