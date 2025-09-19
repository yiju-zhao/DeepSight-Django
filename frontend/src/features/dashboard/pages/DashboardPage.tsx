/**
 * Refactored Dashboard Page - Modern TanStack Query approach
 * Uses React Query for better caching, error handling, and loading states
 *
 * This component is now focused on orchestration and layout, with
 * specific responsibilities delegated to focused sub-components.
 */

import { useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import ReportEditor from '@/features/report/components/ReportEditor';

// Import TanStack Query hooks and components
import { useDashboardData, Report, Podcast } from '../queries';
import DashboardHeader from '../components/DashboardHeader';
import ReportsSection from '../components/ReportsSection';
import PodcastsSection from '../components/PodcastsSection';
import ConferenceSection from '../components/ConferenceSection';
import DashboardActions from '../components/DashboardActions';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';

export default function DashboardPage() {
  const navigate = useNavigate();

  // Modern TanStack Query data management
  const {
    reports,
    podcasts,
    loading,
    error,
    reportsQuery,
    refetch,
  } = useDashboardData();

  // UI state
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
  const [language, setLanguage] = useState<'en' | 'zh'>('en');

  // Memoize expensive computations - MUST be called before any early returns
  const hasContent = useMemo(() =>
    reports.length > 0 || podcasts.length > 0,
    [reports.length, podcasts.length]
  );

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
    // For now, just update local state - proper mutation should be implemented
    setSelectedReport(null);
    // TODO: Implement proper delete mutation with optimistic updates
    console.log('Delete report:', report.id);
    refetch(); // Refetch data after deletion
  }, [refetch]);

  const handleSaveReport = useCallback((report: Report, content: string) => {
    console.log('Saving report:', report.id, content);
    // TODO: Implement proper update mutation with optimistic updates
    refetch(); // Refetch data after save
  }, [refetch]);

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
