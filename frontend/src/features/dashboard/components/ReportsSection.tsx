/**
 * Reports section component for the dashboard
 * Handles display of trending reports with modern Huawei-style design
 * Optimized with React.memo to prevent unnecessary re-renders
 */

import React, { useMemo } from 'react';
import ReportListItem from '@/features/report/components/ReportListItem';
import { Card } from '@/shared/components/ui/card';
import { SectionHeader } from '@/shared/components/ui/section-header';
import { Button } from '@/shared/components/ui/button';
import { FileText } from 'lucide-react';
import { Report } from '../queries';

interface ReportsSectionProps {
  reports: Report[];
  onReportSelect: (report: Report) => void;
  onViewAll?: () => void;
  loading?: boolean;
  className?: string;
}

const ReportsSection: React.FC<ReportsSectionProps> = React.memo(({
  reports,
  onReportSelect,
  onViewAll,
  loading = false,
  className = '',
}) => {
  // Limit to 3 reports for dashboard
  const displayReports = useMemo(() => reports.slice(0, 3), [reports]);

  // Memoize loading skeleton
  const loadingSkeleton = useMemo(() => (
    <Card variant="elevated" className={className}>
      <div className="p-6 space-y-4">
        <div className="h-6 bg-gray-200 rounded animate-pulse w-48" />
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-20 bg-gray-200 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    </Card>
  ), [className]);

  if (loading) {
    return loadingSkeleton;
  }

  if (reports.length === 0) {
    return (
      <Card variant="elevated" className={className}>
        <div className="p-6">
          <SectionHeader title="Trending Reports" />
          <div className="text-center py-8">
            <FileText className="h-12 w-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-sm font-medium text-gray-900 mb-1">No trending reports</h3>
            <p className="text-xs text-gray-500">Check back later for trending research.</p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card variant="elevated" hoverable className={className}>
      <div className="p-6">
        <SectionHeader
          title="Trending Reports"
          action={
            onViewAll && reports.length > 3 && (
              <Button variant="ghost" size="sm" withArrow onClick={onViewAll}>
                View All
              </Button>
            )
          }
        />

        <div className="space-y-3">
          {displayReports.map((report) => (
            <ReportListItem
              key={report.id}
              report={report}
              onSelect={onReportSelect}
            />
          ))}
        </div>

        {onViewAll && reports.length > 3 && (
          <div className="mt-6 pt-4 border-t border-border">
            <Button variant="accent" withArrow onClick={onViewAll} className="w-full md:w-auto">
              View All Reports
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
});

ReportsSection.displayName = 'ReportsSection';

export default ReportsSection;
