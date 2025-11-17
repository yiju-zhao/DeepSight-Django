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
import AppLayout from '@/shared/components/layout/AppLayout';

// Import TanStack Query hooks and components
import { useDashboardData, Report, Podcast } from '../queries';
import ReportsSection from '../components/ReportsSection';
import PodcastsSection from '../components/PodcastsSection';
import ConferenceSection from '../components/ConferenceSection';
import DashboardActions from '../components/DashboardActions';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';
import MainPageHeader from '@/shared/components/common/MainPageHeader';
import { BarChart3 } from 'lucide-react';

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
    navigate('/dashboard/conference');
  }, [navigate]);

  // Loading state
  if (loading) {
    return (
      <AppLayout>
        <LoadingState />
      </AppLayout>
    );
  }

  // Error state
  if (error) {
    return (
      <AppLayout>
        <div className="p-8 bg-transparent min-h-screen">
          <MainPageHeader
            title="Dashboard"
            icon={<BarChart3 className="w-5 h-5 text-white" />}
            iconColor="from-gray-800 to-gray-900"
          />
          <div className="max-w-4xl mx-auto">
            <EmptyState
              icon="⚠️"
              title="Something went wrong"
              description={error}
            />
          </div>
        </div>
      </AppLayout>
    );
  }

  // Show report editor if a report is selected
  if (selectedReport) {
    return (
      <AppLayout>
        <ReportEditor
          report={selectedReport}
          onBack={handleBackToList}
          onDelete={handleDeleteReport}
          onSave={handleSaveReport}
        />
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="flex flex-col min-h-screen bg-transparent">
        <MainPageHeader
          title="Dashboard"
          icon={<BarChart3 className="w-5 h-5 text-white" />}
          iconColor="from-gray-800 to-gray-900"
        />

        <div className="flex-1 px-4 md:px-10 lg:px-20 py-10 md:py-20">
          <div className="max-w-7xl mx-auto space-y-10 md:space-y-20">
            {/* Conference Overview Stats Section */}
            <section className="animate-slide-up">
              <ConferenceSection onNavigateToConferences={handleNavigateToConferences} />
            </section>

            {/* Reports & Podcasts Grid Section (Hidden) */}
            {/*
            <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-8 animate-slide-up-delay-1">
              <div>
                <ReportsSection
                  reports={reports}
                  onReportSelect={handleReportSelect}
                  loading={reportsQuery.isLoading}
                />
              </div>

              <div>
                <PodcastsSection
                  podcasts={podcasts}
                  onPodcastSelect={handlePodcastSelect}
                  loading={loading}
                />
              </div>
            </section>
            */}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
