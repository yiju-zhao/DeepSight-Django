import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useReport, useReportContent, useDeleteReport } from '@/features/report/hooks/useReports';
import { ReportService } from '@/features/report/services/ReportService';
import ReportDetail from '@/features/report/components/ReportDetail';

/**
 * ReportDetailPage component
 * Displays a single report with URL routing support
 * Follows the same pattern as DeepdivePage for consistency
 */
export default function ReportDetailPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState<'preview' | 'edit'>('preview');

  // Fetch report data using React Query
  const {
    data: report,
    isLoading: loadingReport,
    error: loadError,
  } = useReport(reportId || '', { enabled: !!reportId });

  // Fetch report content (only if report is completed)
  const {
    data: contentResponse,
    isLoading: loadingContent,
  } = useReportContent(reportId || '', {
    enabled: !!reportId && report?.status === 'completed',
  });

  // Map ReportContentResponse to ReportContent for the component
  const contentData = contentResponse ? {
    content: contentResponse.content,
    markdown_content: contentResponse.content, // Backend returns markdown in content field
    title: contentResponse.article_title,
  } : undefined;

  // Mutations
  const deleteReportMutation = useDeleteReport();
  const reportService = new ReportService();

  // Handler functions
  const handleBack = () => {
    navigate('/report');
  };

  const handleDelete = async (reportToDelete: any) => {
    if (window.confirm('Are you sure you want to delete this report?')) {
      try {
        await deleteReportMutation.mutateAsync(reportToDelete.id);
        navigate('/report');
      } catch (error) {
        console.error('Failed to delete report:', error);
      }
    }
  };

  const handleDownload = async (reportToDownload: any) => {
    try {
      await reportService.downloadReport(
        reportToDownload.id,
        `${reportToDownload.article_title || 'report'}.pdf`
      );
    } catch (error) {
      console.error('Failed to download report:', error);
    }
  };

  const handleEdit = () => {
    setViewMode('edit');
  };

  const handleSave = (content: string) => {
    // TODO: Implement content save functionality
    console.log('Save content:', content);
    setViewMode('preview');
  };

  const handleContentChange = (content: string) => {
    // TODO: Handle content change if needed
    console.log('Content changed:', content);
  };

  // Loading state
  if (!reportId) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <span className="text-red-500">No report ID provided</span>
      </div>
    );
  }

  if (loadingReport) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <span className="text-gray-500">Loading report...</span>
      </div>
    );
  }

  // Error state
  if (loadError) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-gray-50 p-4">
        <p className="text-red-600 mb-4">
          {loadError instanceof Error ? loadError.message : 'Failed to load report'}
        </p>
        <div className="space-x-4">
          <button
            onClick={handleBack}
            className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
          >
            Back to Reports
          </button>
        </div>
      </div>
    );
  }

  // No report found
  if (!report) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-gray-50 p-4">
        <p className="text-gray-600 mb-4">Report not found</p>
        <button
          onClick={handleBack}
          className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
        >
          Back to Reports
        </button>
      </div>
    );
  }

  // Main render
  return (
    <div className="h-screen bg-gray-50">
      <ReportDetail
        report={report}
        content={contentData}
        isLoading={loadingContent}
        viewMode={viewMode}
        onDownload={handleDownload}
        onDelete={handleDelete}
        onEdit={handleEdit}
        onSave={handleSave}
        onContentChange={handleContentChange}
        onBack={handleBack}
      />
    </div>
  );
}
