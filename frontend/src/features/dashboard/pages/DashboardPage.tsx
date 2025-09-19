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
import MainPageHeader from '@/shared/components/header/MainPageHeader';
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
      <div className="flex flex-col min-h-screen bg-gray-50">
        <MainPageHeader
          title="Dashboard"
          subtitle="AI-powered insights and analytics"
          icon={<BarChart3 className="w-5 h-5 text-white" />}
          iconColor="from-blue-500 to-blue-600"
        />

        <div className="flex-1 p-6 md:p-8 overflow-hidden">
          <div className="max-w-7xl mx-auto h-full">
            {/* Three-Panel Dashboard Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
              {/* Conference Panel */}
              <div className="lg:col-span-1">
                <ConferenceSection onNavigateToConferences={handleNavigateToConferences} />
              </div>

              {/* Reports Panel */}
              <div className="lg:col-span-1">
                {reports.length > 0 ? (
                  <ReportsSection
                    reports={reports}
                    onReportSelect={handleReportSelect}
                  />
                ) : (
                  <div className="bg-white/80 backdrop-blur-sm rounded-xl border border-gray-200 shadow-sm p-6 h-full flex flex-col">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-gray-100 rounded-lg">
                          <div className="h-6 w-6 bg-gray-300 rounded" />
                        </div>
                        <div>
                          <h2 className="text-base font-semibold text-gray-900">Research Reports</h2>
                          <p className="text-sm text-gray-600">AI-generated insights</p>
                        </div>
                      </div>
                    </div>
                    <div className="flex-1 flex items-center justify-center">
                      <div className="text-center">
                        <div className="h-12 w-12 rounded-full border border-dashed border-gray-300 mx-auto mb-4 flex items-center justify-center text-gray-400">
                          <span className="text-lg">📊</span>
                        </div>
                        <h3 className="text-sm font-medium text-gray-900 mb-1">Coming soon</h3>
                        <p className="text-gray-500 text-xs">Report generation features in progress</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Podcasts Panel */}
              <div className="lg:col-span-1">
                {podcasts.length > 0 ? (
                  <PodcastsSection
                    podcasts={podcasts}
                    onPodcastSelect={handlePodcastSelect}
                  />
                ) : (
                  <div className="bg-white/80 backdrop-blur-sm rounded-xl border border-gray-200 shadow-sm p-6 h-full flex flex-col">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-gray-100 rounded-lg">
                          <div className="h-6 w-6 bg-gray-300 rounded" />
                        </div>
                        <div>
                          <h2 className="text-base font-semibold text-gray-900">AI Podcasts</h2>
                          <p className="text-sm text-gray-600">Audio generation</p>
                        </div>
                      </div>
                    </div>
                    <div className="flex-1 flex items-center justify-center">
                      <div className="text-center">
                        <div className="h-12 w-12 rounded-full border border-dashed border-gray-300 mx-auto mb-4 flex items-center justify-center text-gray-400">
                          <span className="text-lg">🎙️</span>
                        </div>
                        <h3 className="text-sm font-medium text-gray-900 mb-1">Coming soon</h3>
                        <p className="text-gray-500 text-xs">Podcast features in progress</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        <DashboardActions
          onViewModeChange={handleViewModeChange}
          onLanguageChange={handleLanguageChange}
          viewMode={viewMode}
          language={language}
        />
      </div>
    </AppLayout>
  );
}
