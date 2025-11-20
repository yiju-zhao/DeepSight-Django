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
import Header from '@/shared/components/layout/Header';
import Footer from '@/shared/components/layout/Footer';

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
    navigate('/conference');
  }, [navigate]);

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Header />
        <main className="flex-grow pt-[var(--header-height)] flex items-center justify-center">
          <LoadingState />
        </main>
        <Footer />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Header />
        <main className="flex-grow pt-[var(--header-height)]">
          <div className="p-8 bg-transparent min-h-screen">
            <MainPageHeader
              label="DEEPSIGHT"
              title="Dashboard"
              subtitle="Overview of your research projects and analytics"
              icon={<BarChart3 className="w-6 h-6 text-[#1E1E1E]" />}
            />
            <div className="max-w-4xl mx-auto">
              <EmptyState
                icon="⚠️"
                title="Something went wrong"
                description={error}
              />
            </div>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  // Show report editor if a report is selected
  if (selectedReport) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Header />
        <main className="flex-grow pt-[var(--header-height)]">
          <ReportEditor
            report={selectedReport}
            onBack={handleBackToList}
            onDelete={handleDeleteReport}
            onSave={handleSaveReport}
          />
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />

      <main className="flex-grow pt-[var(--header-height)]">
        {/* Hero Section / Header */}
        <section className="relative bg-white border-b border-gray-100">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-gray-50 via-white to-white opacity-50"></div>
          <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-12 relative z-10">
            <MainPageHeader
              label="DEEPSIGHT"
              title="Dashboard"
              subtitle="Overview of your research projects and analytics"
              icon={<BarChart3 className="w-6 h-6 text-[#1E1E1E]" />}
            />
          </div>
        </section>

        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="space-y-12">
            {/* Conference Overview Stats Section */}
            <section className="animate-slide-up">
              <ConferenceSection onNavigateToConferences={handleNavigateToConferences} />
            </section>

            {/* Reports & Podcasts Grid Section (Hidden) */}
            {/*
            <section className="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-slide-up-delay-1">
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
      </main>

      <Footer />
    </div>
  );
}
