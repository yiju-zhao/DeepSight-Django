// ====== SOLID PRINCIPLES REFACTORED STUDIO PANEL ======
// This component demonstrates all 5 SOLID principles in action

import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Maximize2, Minimize2, Settings, FileText, Play, Palette, ChevronDown, Trash2, Edit, Download, Save, X, Eye } from 'lucide-react';
import { Button } from "@/shared/components/ui/button";
import { useToast } from "@/shared/components/ui/use-toast";

// ====== DEPENDENCY INVERSION PRINCIPLE (DIP) ======
// Import service abstractions, not concrete implementations
import studioService from "@/features/notebook/services/StudioService";

// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Import focused custom hooks for specific concerns
import { config } from "@/config";
import { PANEL_HEADERS } from "@/features/notebook/config/uiConfig";
import { useNotebookReportJobs, useNotebookPodcastJobs, useReportModels, useDeleteReport, useDeletePodcast } from "@/features/notebook/hooks/studio/useStudio";
import { useGenerationManager } from "@/features/notebook/hooks/studio/useGenerationManager";

// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Import focused UI components
import ReportGenerationForm from './ReportGenerationForm';
import PodcastGenerationForm from './PodcastGenerationForm';
import PodcastAudioPlayer from './PodcastAudioPlayer';
import FileViewer from './FileViewer';

// ====== INTERFACE SEGREGATION PRINCIPLE (ISP) ======
// Import type definitions and prop creators
import {
  StudioPanelProps,
  FileItem,
  SourceItem,
  ReportItem,
  PodcastItem,
  GenerationState
} from './types';

// ====== DEPENDENCY INVERSION PRINCIPLE (DIP) ======
// Service instances - can be injected for testing

// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Main container component focused on orchestration and state coordination
const StudioPanel: React.FC<StudioPanelProps> = ({ 
  notebookId, 
  sourcesListRef, 
  onSelectionChange,
  onOpenModal,
  onCloseModal,
  onToggleExpand,
  isStudioExpanded
}) => {
  const { toast } = useToast();

  // ====== SINGLE RESPONSIBILITY: UI State Management ======
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  const [selectedFileContent, setSelectedFileContent] = useState<string>('');
  const [viewMode, setViewMode] = useState<'preview' | 'edit'>('preview');
  const [isReportPreview, setIsReportPreview] = useState<boolean>(false);
  const [isPreviewingEdits, setIsPreviewingEdits] = useState<boolean>(false);
  const [expandedPodcasts, setExpandedPodcasts] = useState<Set<string>>(new Set());


  // ====== SINGLE RESPONSIBILITY: File Selection State ======
  const [selectedFiles, setSelectedFiles] = useState<FileItem[]>([]);
  const [selectedSources, setSelectedSources] = useState<SourceItem[]>([]);

  // ====== DEPENDENCY INVERSION: Use consolidated overview hooks ======
  const reportJobs = useNotebookReportJobs(notebookId);
  const podcastJobs = useNotebookPodcastJobs(notebookId);
  const reportModels = useReportModels();

  // ====== MUTATIONS: Use optimized deletion hooks ======
  const deleteReportMutation = useDeleteReport(notebookId);
  const deletePodcastMutation = useDeletePodcast(notebookId);

  // ====== COMPLETION HANDLERS ======
  const handleReportComplete = useCallback((jobData: any) => {
    toast({
      title: "Report Generated",
      description: "Your research report has been generated successfully."
    });

    // Auto-select and display the completed report after a delay
    if (jobData && (jobData.id || jobData.jobId)) {
      setTimeout(() => {
        // Find the completed report in the jobs list
        const currentReportJobs = reportJobs.data?.jobs || [];
        const completedReport = currentReportJobs.find((job: any) =>
          (job.id === jobData.id || job.id === jobData.jobId ||
           job.job_id === jobData.id || job.job_id === jobData.jobId) &&
          job.status === 'completed'
        );

        if (completedReport) {
          // Trigger a direct API call to select and display the report
          // This avoids the circular dependency issue
          studioService.getReportContent(completedReport.id || completedReport.job_id, notebookId)
            .then(content => {
              setSelectedFile(completedReport);
              setSelectedFileContent(content.content || content.markdown_content || '');
              setViewMode('preview');
              setIsReportPreview(true);
            })
            .catch(error => {
              console.error('Failed to auto-display completed report:', error);
            });
        }
      }, 1500); // Longer delay to ensure data is available
    }
  }, [reportJobs.data, notebookId, toast]);

  const handlePodcastComplete = useCallback((jobData: any) => {
    toast({
      title: "Podcast Generated",
      description: "Your panel discussion has been generated successfully."
    });
  }, [toast]);

  // ====== SINGLE RESPONSIBILITY: Report generation management ======
  const reportGeneration = useGenerationManager(notebookId, 'report', handleReportComplete);

  // ====== SINGLE RESPONSIBILITY: Podcast generation management ======
  const podcastGeneration = useGenerationManager(notebookId, 'podcast', handlePodcastComplete);

  // Initialize default configs
  useEffect(() => {
    reportGeneration.updateConfig({
      topic: '',
      article_title: '',
      model_provider: 'openai',
      retriever: 'tavily',
      prompt_type: 'general',
      include_image: false,
      include_domains: false,
      time_range: 'ALL',
      model: 'gpt-4'
    });

    podcastGeneration.updateConfig({
      title: '',
      description: '',
      topic: '',
      expert_names: {
        host: '杨飞飞',
        expert1: '奥立昆',
        expert2: '李特曼'
      },
      model: 'gpt-4'
    });
  }, [reportGeneration.updateConfig, podcastGeneration.updateConfig]);

  // Cleanup SSE connections on unmount
  useEffect(() => {
    return () => {
      reportGeneration.cleanup();
      podcastGeneration.cleanup();
    };
  }, [reportGeneration.cleanup, podcastGeneration.cleanup]);


  // ====== JOB STATUS MONITORING ======
  // The new generation manager handles job status monitoring internally via SSE and React Query

  // ====== JOB RECOVERY & PROGRESS SYNC ======
  // The new generation manager handles job recovery and progress sync automatically via queries

  // ====== SINGLE RESPONSIBILITY: Source selection sync ======
  useEffect(() => {
    if (sourcesListRef?.current) {
      const updateSelection = () => {
        const selected = sourcesListRef.current?.getSelectedFiles?.() || [];
        const sources = sourcesListRef.current?.getSelectedSources?.() || [];
        setSelectedFiles(selected);
        setSelectedSources(sources);
      };

      updateSelection();
      onSelectionChange?.(updateSelection);
    }
  }, [sourcesListRef, onSelectionChange]);

  // ====== SINGLE RESPONSIBILITY: Report generation handler ======
  const handleGenerateReport = useCallback(async (configOverrides?: Partial<any>) => {
    try {
      const config = {
        ...configOverrides,
        selected_files_paths: selectedFiles.map((f: FileItem) => f.id),
        model: configOverrides?.model || reportGeneration.config.model || 'gpt-4'
      };

      reportGeneration.generate(config);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast({
        title: "Generation Failed",
        description: errorMessage,
        variant: "destructive"
      });
    }
  }, [reportGeneration.generate, reportGeneration.config.model, selectedFiles, toast]);

  // ====== SINGLE RESPONSIBILITY: Podcast generation handler ======
  const handleGeneratePodcast = useCallback(async (configOverrides?: Partial<any>) => {
    try {
      const config = {
        ...configOverrides,
        source_file_ids: selectedFiles.map((f: FileItem) => f.id),
        model: configOverrides?.model || podcastGeneration.config.model || 'gpt-4'
      };

      podcastGeneration.generate(config);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast({
        title: "Generation Failed",
        description: errorMessage,
        variant: "destructive"
      });
    }
  }, [podcastGeneration.generate, podcastGeneration.config.model, selectedFiles, toast]);

  // ====== SINGLE RESPONSIBILITY: Cancellation handlers ======
  const handleCancelReport = useCallback(async () => {
    try {
      reportGeneration.cancel();
      toast({
        title: "Cancelled",
        description: "Report generation cancelled successfully."
      });
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast({
        title: "Cancel Failed",
        description: `Failed to cancel report generation: ${errorMessage}`,
        variant: "destructive"
      });
    }
  }, [reportGeneration.cancel, toast]);

  const handleCancelPodcast = useCallback(async () => {
    try {
      podcastGeneration.cancel();
      toast({
        title: "Cancelled",
        description: "Podcast generation cancelled successfully."
      });
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast({
        title: "Cancel Failed",
        description: `Failed to cancel podcast generation: ${errorMessage}`,
        variant: "destructive"
      });
    }
  }, [podcastGeneration.cancel, toast]);


  const toggleExpanded = useCallback(() => {
    if (onToggleExpand) {
      onToggleExpand();
    }
  }, [onToggleExpand]);

  const toggleViewMode = useCallback(() => {
    setViewMode(prev => prev === 'preview' ? 'edit' : 'preview');
  }, []);

  // ====== SINGLE RESPONSIBILITY: Data refresh ======
  const handleRefresh = useCallback(() => {
    // Refetch all data
    reportJobs.refetch();
    podcastJobs.refetch();
    reportModels.refetch();
  }, [reportJobs, podcastJobs, reportModels]);

  // ====== SINGLE RESPONSIBILITY: File operations ======
  const handleSelectReport = useCallback(async (report: ReportItem) => {
    try {
      // Use job_id if id is not available, as API might return job_id instead of id
      const reportId = report.id || report.job_id;
      if (!reportId) {
        throw new Error('Report ID not found');
      }
      
      const content = await studioService.getReportContent(reportId, notebookId);
      setSelectedFile(report);
      setSelectedFileContent(content.content || content.markdown_content || '');
      setViewMode('preview');
      setIsReportPreview(true);
    } catch (error) {
      console.error('Failed to load report content:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast({
        title: "Error",
        description: "Failed to load report content: " + errorMessage,
        variant: "destructive"
      });
    }
  }, [studioService, notebookId, toast]);

  const handlePodcastClick = useCallback((podcast: PodcastItem) => {
    const podcastId = podcast.id || podcast.job_id || '';
    setExpandedPodcasts(prev => {
      const newSet = new Set(prev);
      if (newSet.has(podcastId)) {
        newSet.delete(podcastId);
      } else {
        newSet.add(podcastId);
      }
      return newSet;
    });
  }, []);

  const getReportPreview = useCallback((report: ReportItem): string => {
    // Get a two-line preview from content or description
    const content = report.content || report.description || '';
    const lines = content.split('\n').filter((line: string) => line.trim());
    return lines.slice(0, 2).join(' ').substring(0, 120) + (content.length > 120 ? '...' : '');
  }, []);

  const handleDownloadReport = useCallback(async (report: ReportItem) => {
    try {
      const reportId = report.id || report.job_id;
      if (!reportId) {
        throw new Error('Report ID not found');
      }
      
      // Add a small delay to ensure any pending save operations complete
      // This prevents race conditions between save and download
      await new Promise(resolve => setTimeout(resolve, 500));
      
      const filename = `${report.title || report.article_title || 'report'}.pdf`;
      
      // Use notebookService.downloadReportPdf directly instead of studioService.downloadFile
      // This ensures we're using the correct PDF download endpoint
      const blob = await studioService.downloadReportPdf(reportId, notebookId);
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Clean up the blob URL
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
      }, 1000);
      
      toast({
        title: "Download Started",
        description: "Your report is being downloaded as PDF"
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast({
        title: "Download Failed", 
        description: errorMessage,
        variant: "destructive"
      });
    }
  }, [studioService, notebookId, toast]);

  const handleDownloadPodcast = useCallback(async (podcast: PodcastItem) => {
    try {
      const podcastId = podcast.id || podcast.job_id;
      if (!podcastId) {
        throw new Error('Podcast ID not found');
      }
      
      // Use the API service to download the podcast audio as a blob
      const blob = await studioService.downloadPodcastAudio(podcastId, notebookId);
      
      // Create download link and trigger download
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${podcast.title || 'podcast'}.mp3`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Clean up the blob URL
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
      }, 1000);
      
      toast({
        title: "Download Started",
        description: "Your podcast download should begin shortly"
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast({
        title: "Download Failed",
        description: errorMessage, 
        variant: "destructive"
      });
    }
  }, [notebookId, toast]);

  const handleDeleteReport = useCallback(async (report: ReportItem) => {
    if (!confirm('Are you sure you want to delete this report?')) {
      return;
    }

    try {
      const reportId = report.id || report.job_id;
      if (!reportId) {
        throw new Error('Report ID not found');
      }

      // Clear selected file if it's the one being deleted, without navigating to another file
      if (selectedFile?.id === reportId || selectedFile?.job_id === reportId) {
        setSelectedFile(null);
        setSelectedFileContent('');
      }

      // Use the mutation hook for optimized deletion with automatic UI updates
      await deleteReportMutation.mutateAsync(reportId);

      toast({
        title: "Report Deleted",
        description: "The report has been deleted successfully"
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast({
        title: "Delete Failed",
        description: `Failed to delete report: ${errorMessage}`,
        variant: "destructive"
      });
    }
  }, [deleteReportMutation, selectedFile, toast]);

  const handleDeletePodcast = useCallback(async (podcast: PodcastItem) => {
    if (!confirm('Are you sure you want to delete this podcast?')) {
      return;
    }

    try {
      const podcastId = podcast.id || podcast.job_id;
      if (!podcastId) {
        throw new Error('Podcast ID not found');
      }

      // Clear selected file if it's the one being deleted
      if (selectedFile?.id === podcastId || selectedFile?.job_id === podcastId) {
        setSelectedFile(null);
        setSelectedFileContent('');
      }

      // Use the mutation hook for optimized deletion with automatic UI updates
      await deletePodcastMutation.mutateAsync(podcastId);

      toast({
        title: "Podcast Deleted",
        description: "The podcast has been deleted successfully"
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast({
        title: "Delete Failed",
        description: `Failed to delete podcast: ${errorMessage}`,
        variant: "destructive"
      });
    }
  }, [deletePodcastMutation, selectedFile, toast]);

  const handleSaveFile = useCallback(async (content: string) => {
    if (!selectedFile) return;

    try {
      // Use job_id if id is not available, as API expects job_id for reports
      const fileId = selectedFile.id || selectedFile.job_id;
      if (!fileId) {
        throw new Error('File ID not found');
      }

      await studioService.updateReport(fileId, notebookId, content);
      setSelectedFileContent(content);

      // Invalidate report jobs cache to sync changes
      reportJobs.refetch();

      toast({
        title: "File Saved",
        description: "Your changes have been saved and synchronized"
      });
    } catch (error) {
      console.error('Save error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast({
        title: "Save Failed",
        description: `Failed to save: ${errorMessage}`,
        variant: "destructive"
      });
    }
  }, [selectedFile, studioService, reportJobs, notebookId, toast]);

  const handleCloseFile = useCallback(() => {
    setSelectedFile(null);
    setSelectedFileContent('');
    setViewMode('preview');
    setIsReportPreview(false);
    setIsPreviewingEdits(false);
  }, []);

  const handlePreviewEdits = useCallback(() => {
    setIsPreviewingEdits(true);
    setViewMode('preview');
  }, []);

  // ====== OPEN/CLOSED PRINCIPLE (OCP) ======
  // Render method that can be extended without modification
  return (
    <div className="flex flex-col h-full">
      {/* ====== SINGLE RESPONSIBILITY: Header rendering ====== */}
      <div className={`${PANEL_HEADERS.container}`}>
        <div className={PANEL_HEADERS.layout}>
          <div className={PANEL_HEADERS.titleContainer}>
            <div className={PANEL_HEADERS.iconContainer}>
              <Palette className={PANEL_HEADERS.icon} />
            </div>
            <h3 className={PANEL_HEADERS.title}>
              {isReportPreview ? 'Studio/Report' : 'Studio'}
            </h3>
            {(reportGeneration.isGenerating || podcastGeneration.isGenerating) && (
              <div className="flex items-center space-x-2 text-sm text-red-600">
                <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse"></div>
                <span>Generating...</span>
              </div>
            )}
          </div>
          <div className={PANEL_HEADERS.actionsContainer}>
            {isReportPreview && selectedFile ? (
              // Report preview controls
              <>
                {viewMode === 'preview' && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-xs text-gray-500 hover:text-gray-700"
                    onClick={() => setViewMode('edit')}
                  >
                    <Edit className="h-3 w-3 mr-1" />
                    Edit
                  </Button>
                )}
                {viewMode === 'edit' && (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2 text-xs text-blue-600 hover:text-blue-800"
                      onClick={handlePreviewEdits}
                    >
                      <Eye className="h-3 w-3 mr-1" />
                      Preview
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2 text-xs text-gray-500 hover:text-gray-700"
                      onClick={() => handleSaveFile(selectedFileContent)}
                    >
                      <Save className="h-3 w-3 mr-1" />
                      Save
                    </Button>
                  </>
                )}
                {viewMode === 'preview' && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-xs text-gray-500 hover:text-gray-700"
                    onClick={() => handleDownloadReport(selectedFile)}
                  >
                    <Download className="h-3 w-3 mr-1" />
                    Download
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0 text-gray-400 hover:text-gray-600"
                  onClick={toggleExpanded}
                >
                  {isStudioExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0 text-gray-400 hover:text-gray-600"
                  onClick={handleCloseFile}
                >
                  <X className="h-4 w-4" />
                </Button>
              </>
            ) : (
              // Default studio controls
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs text-gray-500 hover:text-gray-700"
                  onClick={handleRefresh}
                  disabled={reportJobs.isLoading || podcastJobs.isLoading || reportModels.isLoading}
                >
                  <RefreshCw className={`h-3 w-3 mr-1 ${reportJobs.isLoading || podcastJobs.isLoading || reportModels.isLoading ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs text-gray-500 hover:text-gray-700"
                  onClick={() => {
                    // Import AdvancedSettingsModal component dynamically
                    import('./AdvancedSettingsModal').then(({ default: AdvancedSettingsModal }) => {
                      const settingsContent = (
                        <AdvancedSettingsModal
                          isOpen={true}
                          onClose={() => onCloseModal('advancedSettings')}
                          reportConfig={reportGeneration.config}
                          podcastConfig={podcastGeneration.config}
                          onReportConfigChange={reportGeneration.updateConfig}
                          onPodcastConfigChange={podcastGeneration.updateConfig}
                          availableModels={reportModels.data || {}}
                        />
                      );
                      onOpenModal('advancedSettings', settingsContent);
                    });
                  }}
                  title="Advanced Settings"
                >
                  <Settings className="h-3 w-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0 text-gray-400 hover:text-gray-600"
                  onClick={toggleExpanded}
                >
                  {isStudioExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                </Button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ====== SINGLE RESPONSIBILITY: Main content area ====== */}
      {!isReportPreview ? (
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* ====== FIXED SECTIONS: Generation Forms ====== */}
          <div className="flex-shrink-0 p-4 space-y-4 bg-gray-50/50 border-b border-gray-200/60">
            {/* ====== LISKOV SUBSTITUTION PRINCIPLE (LSP) ====== */}
            {/* Both forms follow the same interface contract */}
            
            <ReportGenerationForm
              config={reportGeneration.config}
              onConfigChange={reportGeneration.updateConfig}
              availableModels={reportModels.data || {}}
              generationState={{
                state: reportGeneration.isGenerating ? GenerationState.GENERATING : GenerationState.IDLE,
                progress: reportGeneration.progress,
                error: reportGeneration.error || undefined,
                isGenerating: reportGeneration.isGenerating
              }}
              onGenerate={handleGenerateReport}
              onCancel={handleCancelReport}
              selectedFiles={selectedFiles}
              onOpenModal={onOpenModal}
              onCloseModal={onCloseModal}
            />

            <PodcastGenerationForm
              config={podcastGeneration.config}
              onConfigChange={podcastGeneration.updateConfig}
              generationState={{
                state: podcastGeneration.isGenerating ? GenerationState.GENERATING : GenerationState.IDLE,
                progress: podcastGeneration.progress,
                error: podcastGeneration.error || undefined
              }}
              onGenerate={handleGeneratePodcast}
              onCancel={handleCancelPodcast}
              selectedFiles={selectedFiles}
              selectedSources={selectedSources}
              onOpenModal={onOpenModal}
              onCloseModal={onCloseModal}
            />
          </div>

          {/* ====== SCROLLABLE SECTION: Generated Files List ====== */}
          <div className="flex-1 overflow-auto scrollbar-overlay">
            {(reportJobs.jobs.length > 0 || podcastJobs.jobs.length > 0) ? (() => {
              // Combine reports and podcasts into a unified list
              const allItems = [
                ...reportJobs.jobs.map((report: ReportItem) => ({
                  ...report,
                  type: 'report',
                  created_at: report.created_at || new Date().toISOString()
                })),
                ...podcastJobs.jobs.map((podcast: PodcastItem) => ({
                  ...podcast,
                  type: 'podcast',
                  created_at: podcast.created_at || new Date().toISOString()
                }))
              ];

              // Sort by creation date, newest first
              allItems.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

              return (
                <div className="p-6">
                  <div className="space-y-3">
                    {allItems.map((item: any, index: number) => {
                      const itemId = item.id || item.job_id || index.toString();
                      
                      if (item.type === 'report') {
                        // Check if this report is currently being generated
                        const isGenerating = item.status === 'running' || item.status === 'pending' ||
                                            (reportGeneration.activeJob && reportGeneration.activeJob.jobId === (item.id || item.job_id));

                        return (
                          <div
                            key={`report-${itemId}`}
                            className={`p-4 rounded-xl transition-all duration-500 cursor-pointer group border transform hover:scale-[1.01] animate-slide-in ${
                              isGenerating
                                ? 'bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200 animate-pulse animate-gentle-bounce shadow-lg relative overflow-hidden'
                                : 'bg-white hover:bg-gray-50 border-gray-200 hover:border-gray-300'
                            }`}
                            onClick={() => handleSelectReport(item)}
                          >
                            {/* Shimmer overlay for generating state */}
                            {isGenerating && (
                              <div className="absolute inset-0 -skew-x-12 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer"></div>
                            )}
                            <div className="flex items-start space-x-3 relative z-10">
                              <div className={`w-8 h-8 rounded-lg flex items-center justify-center shadow-sm flex-shrink-0 mt-1 ${
                                isGenerating
                                  ? 'bg-blue-600 animate-pulse'
                                  : 'bg-blue-600'
                              }`}>
                                <FileText className="h-4 w-4 text-white" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <h4 className={`text-sm font-semibold mb-2 truncate ${
                                  isGenerating ? 'text-blue-700' : 'text-gray-900 group-hover:text-blue-700'
                                }`}>
                                  {item.title || 'Research Report'}
                                  {isGenerating && (
                                    <span className="ml-2 inline-flex items-center px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                                      <div className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-ping mr-1"></div>
                                      Generating...
                                    </span>
                                  )}
                                </h4>
                                <p className="text-xs text-gray-600 leading-relaxed mb-2">
                                  {isGenerating
                                    ? (item.progress || reportGeneration.progress || 'Starting report generation...')
                                    : getReportPreview(item)
                                  }
                                </p>
                                <div className="flex items-center text-xs text-gray-500">
                                  <span>{new Date(item.created_at).toLocaleDateString()}</span>
                                  <span className="mx-2">•</span>
                                  <span>Report</span>
                                  <span className="mx-2">•</span>
                                  <span>{isGenerating ? 'Generating...' : 'Click to view'}</span>
                                </div>
                              </div>
                              <div className="opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 w-8 p-0 text-gray-400 hover:text-red-600 hover:bg-red-50"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDeleteReport(item);
                                  }}
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </div>
                            </div>
                          </div>
                        );
                      } else if (item.type === 'podcast') {
                        const isExpanded = expandedPodcasts.has(itemId);
                        // Check if this podcast is currently being generated
                        const isGenerating = item.status === 'running' || item.status === 'pending' ||
                                            (podcastGeneration.activeJob && podcastGeneration.activeJob.jobId === (item.id || item.job_id));

                        return (
                          <div
                            key={`podcast-${itemId}`}
                            className={`rounded-xl border transition-all duration-500 overflow-hidden transform hover:scale-[1.01] animate-slide-in ${
                              isGenerating
                                ? 'bg-gradient-to-r from-purple-50 to-pink-50 border-purple-200 animate-pulse animate-gentle-bounce shadow-lg relative'
                                : 'bg-white border-gray-200 hover:border-gray-300'
                            }`}
                          >
                            {/* Shimmer overlay for generating state */}
                            {isGenerating && (
                              <div className="absolute inset-0 -skew-x-12 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer"></div>
                            )}
                            {/* Podcast Header */}
                            <div
                              className="p-4 cursor-pointer hover:bg-gray-50 transition-colors duration-200 group relative z-10"
                              onClick={() => handlePodcastClick(item)}
                            >
                              <div className="flex items-center space-x-3">
                                <div className={`w-8 h-8 bg-purple-600 rounded-lg flex items-center justify-center shadow-sm flex-shrink-0 ${
                                  isGenerating ? 'animate-pulse' : ''
                                }`}>
                                  {isExpanded ? (
                                    <ChevronDown className="h-4 w-4 text-white" />
                                  ) : (
                                    <Play className="h-4 w-4 text-white" />
                                  )}
                                </div>
                                <div className="flex-1 min-w-0">
                                  <h4 className={`text-sm font-semibold truncate ${
                                    isGenerating ? 'text-purple-700' : 'text-gray-900 hover:text-purple-700'
                                  }`}>
                                    {item.title || 'Panel Discussion'}
                                    {isGenerating && (
                                      <span className="ml-2 inline-flex items-center px-2 py-1 text-xs font-medium bg-purple-100 text-purple-800 rounded-full">
                                        <div className="w-1.5 h-1.5 bg-purple-600 rounded-full animate-ping mr-1"></div>
                                        Generating...
                                      </span>
                                    )}
                                  </h4>
                                  <div className="flex items-center text-xs text-gray-500 mt-1">
                                    {isGenerating && (item.progress || podcastGeneration.progress) && (
                                      <div className="flex items-center text-purple-600 mb-1">
                                        <span className="text-xs">{item.progress || podcastGeneration.progress}</span>
                                      </div>
                                    )}
                                    <span>{new Date(item.created_at).toLocaleDateString()}</span>
                                    <span className="mx-2">•</span>
                                    <span>Podcast</span>
                                    <span className="mx-2">•</span>
                                    <span>{isGenerating ? 'Generating...' : `Click to ${isExpanded ? 'collapse' : 'play'}`}</span>
                                  </div>
                                </div>
                                <div className="flex-shrink-0 flex items-center space-x-2">
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-8 w-8 p-0 text-gray-400 hover:text-red-600 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-opacity"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleDeletePodcast(item);
                                    }}
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                  <div className={`w-2 h-2 rounded-full transition-colors ${isExpanded ? 'bg-purple-400' : 'bg-gray-300'}`}></div>
                                </div>
                              </div>
                            </div>

                            {/* Expanded Audio Player */}
                            {isExpanded && (
                              <div className="border-t border-gray-100 p-4 bg-gray-50">
                                <PodcastAudioPlayer
                                  podcast={item}
                                  onDownload={() => handleDownloadPodcast(item)}
                                  onDelete={() => handleDeletePodcast(item)}
                                  notebookId={notebookId}
                                />
                              </div>
                            )}
                          </div>
                        );
                      }
                      return null;
                    })}
                  </div>
                </div>
              );
            })() : (
              <div className="flex-1 flex items-center justify-center p-8">
                <div className="text-center">
                  <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
                    <FileText className="h-8 w-8 text-gray-400" />
                  </div>
                  <h3 className="text-sm font-medium text-gray-900 mb-1">No generated content yet</h3>
                  <p className="text-xs text-gray-500">Create a research report or podcast to see it here</p>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-auto p-0 scrollbar-overlay">
          {/* Report preview content when viewing a specific report */}
        </div>
      )}

      {/* ====== SINGLE RESPONSIBILITY: File viewer overlay ====== */}
      {selectedFile && (
        <FileViewer
          file={selectedFile}
          content={selectedFileContent}
          isExpanded={isStudioExpanded || false}
          viewMode={viewMode}
          onClose={handleCloseFile}
          onEdit={() => {
            setViewMode('edit');
            setIsPreviewingEdits(false);
          }}
          onSave={handleSaveFile}
          onDownload={selectedFile.audio_file ? 
            () => handleDownloadPodcast(selectedFile) : 
            () => handleDownloadReport(selectedFile)
          }
          onToggleExpand={toggleExpanded}
          onToggleViewMode={toggleViewMode}
          onContentChange={setSelectedFileContent}
          notebookId={notebookId}
          useMinIOUrls={config.USE_MINIO_URLS}
          hideHeader={isReportPreview}
          isPreviewingEdits={isPreviewingEdits}
        />
      )}

    </div>
  );
};

export default StudioPanel;
