import React, { useState, useMemo } from 'react';
import { useReportsList, useDeleteReport } from '@/features/report/hooks/useReports';
import ReportList from "@/features/report/components/ReportList";
import ReportFilters from "@/features/report/components/ReportFilters";
import ReportStats from "@/features/report/components/ReportStats";
import ReportDetail from "@/features/report/components/ReportDetail";
import { Report, ReportFilters as ReportFiltersType } from "@/features/report/types/type";
import { Report as QueryReport } from "@/features/report/hooks/useReports";
import { useNotebookJobStream } from '@/shared/hooks/useNotebookJobStream';
import Header from '@/shared/components/layout/Header';
import { FileText, Sparkles } from 'lucide-react';

const ReportPage: React.FC = () => {
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortOrder, setSortOrder] = useState<'recent' | 'oldest' | 'title'>('recent');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [filters, setFilters] = useState<ReportFiltersType>({});

  // Fetch reports using React Query
  // No automatic polling - SSE handles real-time updates
  const { data: reportsResponse, isLoading, error } = useReportsList(undefined, {
    enabled: true,
    // No refetchInterval - SSE handles real-time updates via useNotebookJobStream
  });

  // Enable SSE for real-time updates (if notebook filter is set)
  // Note: Reports may not always have notebook_id, so SSE is optional enhancement
  useNotebookJobStream({
    notebookId: filters.notebook_id,
    enabled: !!filters.notebook_id,
    onConnected: (nbId) => {
      // Sync current state when SSE reconnects (e.g., after page refresh)
      console.log('[ReportPage] SSE connected, syncing report list');
      // Since this is the global report list, we don't have notebook-specific keys
      // The default invalidation in the hook will handle this
    },
  });

  // Extract raw API reports array from response
  const reports = reportsResponse?.reports || [];

  // Map API reports (QueryReport) to UI domain type (Report)
  const mappedReports: Report[] = useMemo(() => {
    return reports.map((r: QueryReport): Report => ({
      id: r.job_id, // Use job_id as canonical id for actions
      job_id: r.job_id,
      title: r.title,
      article_title: r.article_title,
      description: undefined,
      content: r.has_content ? '' : undefined,
      markdown_content: undefined,
      status: r.status,
      progress: r.progress,
      topic: undefined,
      model_provider: undefined,
      retriever: undefined,
      prompt_type: undefined,
      include_image: undefined,
      include_domains: undefined,
      time_range: undefined,
      notebook_id: undefined,
      source_ids: undefined,
      created_at: r.created_at,
      updated_at: r.updated_at,
      user: undefined,
      error_message: r.error,
      result_metadata: undefined,
      file_metadata: undefined,
      generated_files: undefined,
      processing_logs: undefined,
      main_report_object_key: undefined,
      figure_data_object_key: undefined,
    }));
  }, [reports]);

  // Delete mutation
  const deleteReportMutation = useDeleteReport();

  // Calculate stats from reports (QueryReport type from API)
  const stats = useMemo(() => ({
    total: mappedReports.length,
    completed: mappedReports.filter((r: Report) => r.status === 'completed').length,
    failed: mappedReports.filter((r: Report) => r.status === 'failed').length,
    pending: mappedReports.filter((r: Report) => r.status === 'pending').length,
    running: mappedReports.filter((r: Report) => r.status === 'running').length,
    cancelled: mappedReports.filter((r: Report) => r.status === 'cancelled').length,
  }), [mappedReports]);

  // Filter and sort reports
  const filteredReports = useMemo(() => {
    let filtered: Report[] = mappedReports;

    // Apply search filter
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      filtered = filtered.filter((report: Report) =>
        report.title?.toLowerCase().includes(searchLower) ||
        report.topic?.toLowerCase().includes(searchLower) ||
        report.content?.toLowerCase().includes(searchLower)
      );
    }

    // Apply other filters
    if (filters.status) {
      filtered = filtered.filter((report: Report) => report.status === filters.status);
    }
    if (filters.model_provider) {
      filtered = filtered.filter((report: Report) => report.model_provider === filters.model_provider);
    }
    if (filters.notebook_id) {
      filtered = filtered.filter((report: Report) => report.notebook_id === filters.notebook_id);
    }

    // Apply sorting
    switch (sortOrder) {
      case 'recent':
        return filtered.sort((a: Report, b: Report) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      case 'oldest':
        return filtered.sort((a: Report, b: Report) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
      case 'title':
        return filtered.sort((a: Report, b: Report) => (a.title || '').localeCompare(b.title || ''));
      default:
        return filtered;
    }
  }, [mappedReports, searchTerm, filters, sortOrder]);

  const handleSelectReport = (report: Report) => {
    setSelectedReport(report);
    setShowDetail(true);
  };

  const handleBackToList = () => {
    setShowDetail(false);
    setSelectedReport(null);
  };

  const handleSearchChange = (term: string) => {
    setSearchTerm(term);
  };

  const handleSortChange = (order: 'recent' | 'oldest' | 'title') => {
    setSortOrder(order);
  };

  const handleViewModeChange = (mode: 'grid' | 'list') => {
    setViewMode(mode);
  };

  const handleFiltersChange = (newFilters: ReportFiltersType) => {
    setFilters(newFilters);
  };

  const handleDownloadReport = (report: Report) => {
    // This would be implemented with the download action
    console.log('Downloading report:', report.id);
  };

  const handleDeleteReport = async (report: Report) => {
    try {
      await deleteReportMutation.mutateAsync(report.id);
    } catch (error) {
      console.error('Failed to delete report:', error);
    }
  };

  const handleEditReport = (report: Report) => {
    // This would navigate to edit mode
    console.log('Editing report:', report.id);
  };

  if (showDetail && selectedReport) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Header />
        <main className="flex-grow pt-[var(--header-height)]">
          <ReportDetail
            report={selectedReport}
            isLoading={isLoading}
            onDownload={handleDownloadReport}
            onDelete={handleDeleteReport}
            onEdit={handleEditReport}
            onBack={handleBackToList}
          />
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      <main className="flex-grow pt-[var(--header-height)]">
        {/* Modern Page Header */}
        <section className="relative bg-white border-b border-gray-100">
          <div className="absolute inset-0 bg-gradient-to-b from-gray-50/50 to-white/20 pointer-events-none" />
          <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-12 relative z-10">
            <div className="max-w-3xl">
              <div className="flex items-center gap-2 mb-4">
                <span className="px-3 py-1 rounded-full bg-emerald-50 text-xs font-medium text-emerald-600 flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  Intelligence
                </span>
              </div>
              <h1 className="text-4xl font-bold text-[#1E1E1E] tracking-tight mb-4">
                Research Reports
              </h1>
              <p className="text-lg text-gray-500 leading-relaxed">
                Generate, manage, and analyze your AI-powered research reports.
              </p>
            </div>
          </div>
        </section>

        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {/* Stats */}
          <div className="mb-8">
            <ReportStats stats={stats} />
          </div>

          {/* Filters and Controls */}
          <div className="mb-8 bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <ReportFilters
              filters={filters}
              onFiltersChange={handleFiltersChange}
              stats={stats}
            />

            {/* Search and View Controls */}
            <div className="mt-6 pt-6 border-t border-gray-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="flex-1 max-w-md">
                <input
                  type="text"
                  placeholder="Search reports..."
                  value={searchTerm}
                  onChange={(e) => handleSearchChange(e.target.value)}
                  className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-black/5 focus:border-black/20 transition-all"
                />
              </div>

              <div className="flex items-center gap-4">
                {/* Sort Order */}
                <select
                  value={sortOrder}
                  onChange={(e) => handleSortChange(e.target.value as 'recent' | 'oldest' | 'title')}
                  className="px-4 py-2.5 bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-black/5 focus:border-black/20 transition-all text-sm font-medium text-gray-700"
                >
                  <option value="recent">Most Recent</option>
                  <option value="oldest">Oldest First</option>
                  <option value="title">Title A-Z</option>
                </select>

                {/* View Mode */}
                <div className="flex bg-gray-100 p-1 rounded-lg">
                  <button
                    onClick={() => handleViewModeChange('grid')}
                    className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${viewMode === 'grid'
                        ? 'bg-white text-black shadow-sm'
                        : 'text-gray-500 hover:text-gray-900'
                      }`}
                  >
                    Grid
                  </button>
                  <button
                    onClick={() => handleViewModeChange('list')}
                    className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${viewMode === 'list'
                        ? 'bg-white text-black shadow-sm'
                        : 'text-gray-500 hover:text-gray-900'
                      }`}
                  >
                    List
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="mb-8 bg-red-50 border border-red-100 rounded-xl p-4 flex items-center gap-3">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <p className="text-sm text-red-800 font-medium">
                {error instanceof Error ? error.message : 'An error occurred while loading reports'}
              </p>
            </div>
          )}

          {/* Reports List */}
          <div className="bg-transparent">
            <ReportList
              reports={filteredReports}
              isLoading={isLoading}
              onSelectReport={handleSelectReport}
              onDownloadReport={handleDownloadReport}
              onDeleteReport={handleDeleteReport}
              onEditReport={handleEditReport}
              selectedReportId={selectedReport?.id}
              viewMode={viewMode}
            />
          </div>

          {/* Empty State */}
          {!isLoading && filteredReports.length === 0 && (
            <div className="flex flex-col items-center justify-center py-24 bg-white rounded-2xl border border-dashed border-gray-200">
              <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mb-4">
                <FileText className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No reports found</h3>
              <p className="text-gray-500 text-center max-w-sm">
                {searchTerm || Object.keys(filters).length > 0
                  ? 'Try adjusting your search or filters to find what you are looking for.'
                  : 'Get started by creating your first research report in the Notebook.'
                }
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default ReportPage;
