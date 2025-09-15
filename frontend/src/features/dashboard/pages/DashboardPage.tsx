/**
 * Refactored Dashboard Page - Now follows Single Responsibility Principle
 *
 * This component is now focused on orchestration and layout, with
 * specific responsibilities delegated to focused sub-components.
 */

import { useState } from 'react';
import ReportEditor from '@/features/report/components/ReportEditor';

// Import custom hooks and components
import { useDashboardData, Report, Podcast } from '../hooks/useDashboardData';
import DashboardHeader from '../components/DashboardHeader';
import ReportsSection from '../components/ReportsSection';
import PodcastsSection from '../components/PodcastsSection';
import DashboardActions from '../components/DashboardActions';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';

export default function DashboardPage() {
  // Centralized data management
  const {
    reports,
    podcasts,
    loading,
    error,
    deleteReport,
    updateReport,
  } = useDashboardData();

  // UI state
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
  const [language, setLanguage] = useState<'en' | 'zh'>('en');

  // Event handlers
  const handleReportSelect = (report: Report) => {
    setSelectedReport(report);
  };

  const handlePodcastSelect = (podcast: Podcast) => {
    console.log('Selected podcast:', podcast);
    // TODO: Implement podcast selection logic
  };

  const handleViewModeChange = () => {
    setViewMode(prev => prev === 'list' ? 'grid' : 'list');
  };

  const handleLanguageChange = () => {
    setLanguage(prev => prev === 'en' ? 'zh' : 'en');
  };

  const handleBackToList = () => {
    setSelectedReport(null);
  };

  const handleDeleteReport = (report: Report) => {
    deleteReport(report.id);
    setSelectedReport(null);
  };

  const handleSaveReport = (report: Report, content: string) => {
    updateReport(report.id, { content });
    console.log('Saving report:', report.id, content);
    // TODO: Implement API call to save content
  };

  // Loading state
  if (loading) {
    return <LoadingState />;
  }

  // Error state
  if (error) {
    return (
      <div className="p-8 bg-white min-h-screen">
        <DashboardHeader />
        <div className="max-w-4xl mx-auto">
          <EmptyState
            icon="⚠️"
            title="Something went wrong"
            description={error}
          />
        </div>
      </div>
    );
  }

  // Show report editor if a report is selected
  if (selectedReport) {
    return (
      <ReportEditor
        report={selectedReport}
        onBack={handleBackToList}
        onDelete={handleDeleteReport}
        onSave={handleSaveReport}
      />
    );
  }

  const hasContent = reports.length > 0 || podcasts.length > 0;

  return (
    <div className="p-8 bg-white min-h-screen">
      <DashboardHeader />

      <div className="max-w-4xl mx-auto">
        {hasContent ? (
          <>
            <ReportsSection
              reports={reports}
              onReportSelect={handleReportSelect}
            />
            <PodcastsSection
              podcasts={podcasts}
              onPodcastSelect={handlePodcastSelect}
            />
          </>
        ) : (
          <EmptyState />
        )}
      </div>

      <DashboardActions
        onViewModeChange={handleViewModeChange}
        onLanguageChange={handleLanguageChange}
        viewMode={viewMode}
        language={language}
      />
    </div>
  );
}
