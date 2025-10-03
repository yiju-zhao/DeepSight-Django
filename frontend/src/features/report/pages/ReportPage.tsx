import React, { useState, useMemo } from 'react';
import { useReportsList, useDeleteReport } from '@/features/report/hooks/useReports';
import ReportList from "@/features/report/components/ReportList";
import ReportFilters from "@/features/report/components/ReportFilters";
import ReportStats from "@/features/report/components/ReportStats";
import ReportDetail from "@/features/report/components/ReportDetail";
import { Report, ReportFilters as ReportFiltersType } from "@/features/report/types/type";
import { Report as QueryReport } from "@/features/report/hooks/useReports";

const ReportPage: React.FC = () => {
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortOrder, setSortOrder] = useState<'recent' | 'oldest' | 'title'>('recent');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [filters, setFilters] = useState<ReportFiltersType>({});

  // Fetch reports using React Query
  const { data: reportsResponse, isLoading, error } = useReportsList(undefined, {
    enabled: true,
    refetchInterval: 5000, // Refresh every 5 seconds for active jobs
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
      <ReportDetail
        report={selectedReport}
        isLoading={isLoading}
        onDownload={handleDownloadReport}
        onDelete={handleDeleteReport}
        onEdit={handleEditReport}
        onBack={handleBackToList}
      />
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Research Reports</h1>
          <p className="mt-2 text-gray-600">
            Generate and manage your research reports
          </p>
        </div>

        {/* Stats */}
        <div className="mb-6">
          <ReportStats stats={stats} />
        </div>

        {/* Filters and Controls */}
        <div className="mb-6 bg-white rounded-lg shadow p-6">
          <ReportFilters
            filters={filters}
            onFiltersChange={handleFiltersChange}
            stats={stats}
          />

          {/* Search and View Controls */}
          <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex-1 max-w-md">
              <input
                type="text"
                placeholder="Search reports..."
                value={searchTerm}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex items-center gap-4">
              {/* Sort Order */}
              <select
                value={sortOrder}
                onChange={(e) => handleSortChange(e.target.value as 'recent' | 'oldest' | 'title')}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="recent">Most Recent</option>
                <option value="oldest">Oldest First</option>
                <option value="title">Title A-Z</option>
              </select>

              {/* View Mode */}
              <div className="flex border border-gray-300 rounded-md">
                <button
                  onClick={() => handleViewModeChange('grid')}
                  className={`px-3 py-2 ${
                    viewMode === 'grid'
                      ? 'bg-blue-500 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-50'
                  } rounded-l-md`}
                >
                  Grid
                </button>
                <button
                  onClick={() => handleViewModeChange('list')}
                  className={`px-3 py-2 ${
                    viewMode === 'list'
                      ? 'bg-blue-500 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-50'
                  } rounded-r-md`}
                >
                  List
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-800">{error instanceof Error ? error.message : 'An error occurred'}</p>
              </div>
            </div>
          </div>
        )}

        {/* Reports List */}
        <div className="bg-white rounded-lg shadow">
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
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No reports found</h3>
            <p className="mt-1 text-sm text-gray-500">
              {searchTerm || Object.keys(filters).length > 0
                ? 'Try adjusting your search or filters.'
                : 'Get started by creating your first research report.'
              }
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportPage;
