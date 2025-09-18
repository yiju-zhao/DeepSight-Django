/**
 * Refactored Dashboard Page - Now follows Single Responsibility Principle
 * Optimized for performance with React.memo, useCallback, and useMemo
 *
 * This component is now focused on orchestration and layout, with
 * specific responsibilities delegated to focused sub-components.
 */

import { useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import ReportEditor from '@/features/report/components/ReportEditor';

// Import custom hooks and components
import { useDashboardData, Report, Podcast } from '../hooks/useDashboardData';
import DashboardHeader from '../components/DashboardHeader';
import ReportsSection from '../components/ReportsSection';
import PodcastsSection from '../components/PodcastsSection';
import ConferenceSection from '../components/ConferenceSection';
import DashboardActions from '../components/DashboardActions';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';

export default function DashboardPage() {
  const navigate = useNavigate();

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

  // Event handlers - Memoized to prevent unnecessary re-renders
  const handleReportSelect = useCallback((report: Report) => {
    setSelectedReport(report);
  }, []);

  const handlePodcastSelect = useCallback((podcast: Podcast) => {
    console.log('Selected podcast:', podcast);
    // TODO: Implement podcast selection logic
  }, []);

  const handleViewModeChange = useCallback(() => {
    setViewMode(prev => prev === 'list' ? 'grid' : 'list');
  }, []);

  const handleLanguageChange = useCallback(() => {
    setLanguage(prev => prev === 'en' ? 'zh' : 'en');
  }, []);

  const handleBackToList = useCallback(() => {
    setSelectedReport(null);
  }, []);

  const handleDeleteReport = useCallback((report: Report) => {
    deleteReport(report.id);
    setSelectedReport(null);
  }, [deleteReport]);

  const handleSaveReport = useCallback((report: Report, content: string) => {
    updateReport(report.id, { content });
    console.log('Saving report:', report.id, content);
    // TODO: Implement API call to save content
  }, [updateReport]);

  const handleNavigateToConferences = useCallback(() => {
    navigate('/conferences/dashboard');
  }, [navigate]);

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

  // Memoize expensive computations
  const hasContent = useMemo(() =>
    reports.length > 0 || podcasts.length > 0,
    [reports.length, podcasts.length]
  );

  return (
    <div className="p-8 bg-white min-h-screen">
      <DashboardHeader />

      <div className="max-w-4xl mx-auto space-y-8">
        {/* Conference Analytics Section - Always show */}
        <ConferenceSection onNavigateToConferences={handleNavigateToConferences} />

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
