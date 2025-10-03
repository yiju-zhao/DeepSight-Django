// ====== SOLID PRINCIPLES REFACTORED STUDIO PANEL ======
// This component demonstrates all 5 SOLID principles in action

import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Maximize2, Minimize2, Settings, FileText, Palette, ChevronDown, Trash2, Edit, Download, Save, X, Eye, BookOpen, Headphones, Clock, Database, Users } from 'lucide-react';
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

  // Prevent body scroll when a file/report is open
  useEffect(() => {
    if (selectedFile) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [selectedFile]);


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

    // Force immediate refetch of report jobs to ensure completed report appears
    reportJobs.refetch();

    // Auto-select and display the completed report after a brief delay
    if (jobData && (jobData.id || jobData.jobId)) {
      setTimeout(() => {
        // Force another refetch to get the most current data
        reportJobs.refetch().then(() => {
          // Find the completed report in the refreshed jobs list
          const currentReportJobs = reportJobs.data?.jobs || [];
          const completedReport = currentReportJobs.find((job: any) =>
            (job.id === jobData.id || job.id === jobData.jobId ||
             job.job_id === jobData.id || job.job_id === jobData.jobId) &&
            job.status === 'completed'
          );

          if (completedReport) {
            // Trigger a direct API call to select and display the report
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
        });
      }, 500); // Shorter delay with explicit refetch
    }
  }, [reportJobs.data, notebookId, toast]);

  const handlePodcastComplete = useCallback((jobData: any) => {
    toast({
      title: "Podcast Generated",
      description: "Your panel discussion has been generated successfully."
    });

    // Force immediate refetch of podcast jobs to ensure completed podcast appears
    podcastJobs.refetch();
  }, [toast, podcastJobs]);

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
        source_ids: selectedFiles.map((f: FileItem) => f.id),
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

  // ====== CANCELLATION HANDLING ======
  // Cancellation is now handled through delete buttons on generating report/podcast cards
  // See handleDeleteReport and handleDeletePodcast functions


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
      const reportId = report.id;
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
    const podcastId = podcast.id || '';
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

  const getRelativeTime = useCallback((dateString: string): string => {
    const now = new Date();
    const date = new Date(dateString);
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 60) return 'Just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)}d ago`;
    return date.toLocaleDateString();
  }, []);

  const getSourceCount = useCallback((item: any): number => {
    // Extract source count from various possible properties
    return item.source_count || item.selected_files_count || item.sources?.length || selectedFiles.length || 0;
  }, [selectedFiles.length]);

  const handleDownloadReport = useCallback(async (report: ReportItem) => {
    try {
      const reportId = report.id;
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
      const podcastId = podcast.id;
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
    const isGenerating = report.status === 'running' || report.status === 'pending' ||
                        (reportGeneration.activeJob && reportGeneration.activeJob.jobId === report.id);

    const confirmMessage = isGenerating
      ? 'Are you sure you want to cancel and delete this report?'
      : 'Are you sure you want to delete this report?';

    if (!confirm(confirmMessage)) {
      return;
    }

    try {
      const reportId = report.id;
      if (!reportId) {
        throw new Error('Report ID not found');
      }

      // Clear selected file if it's the one being deleted
      if (selectedFile?.id === reportId) {
        setSelectedFile(null);
        setSelectedFileContent('');
      }

      if (isGenerating) {
        // Cancel and delete the generation synchronously via the backend
        await reportGeneration.cancel(reportId);

        // Force immediate refresh of the job list to remove the cancelled job
        await reportJobs.refetch();

        toast({
          title: "Report Cancelled",
          description: "Report generation has been cancelled and removed"
        });
      } else {
        // Delete the completed report
        await deleteReportMutation.mutateAsync(reportId);
        toast({
          title: "Report Deleted",
          description: "The report has been deleted successfully"
        });
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      const actionText = isGenerating ? 'cancel' : 'delete';
      toast({
        title: `${actionText === 'cancel' ? 'Cancel' : 'Delete'} Failed`,
        description: `Failed to ${actionText} report: ${errorMessage}`,
        variant: "destructive"
      });
    }
  }, [deleteReportMutation, selectedFile, toast, reportGeneration]);

  const handleDeletePodcast = useCallback(async (podcast: PodcastItem) => {
    const isGenerating = podcast.status === 'running' || podcast.status === 'pending' ||
                        (podcastGeneration.activeJob && podcastGeneration.activeJob.jobId === podcast.id);

    const confirmMessage = isGenerating
      ? 'Are you sure you want to cancel this podcast generation?'
      : 'Are you sure you want to delete this podcast?';

    if (!confirm(confirmMessage)) {
      return;
    }

    try {
      const podcastId = podcast.id;
      if (!podcastId) {
        throw new Error('Podcast ID not found');
      }

      // Clear selected file if it's the one being deleted/cancelled
      if (selectedFile?.id === podcastId) {
        setSelectedFile(null);
        setSelectedFileContent('');
      }

      if (isGenerating) {
        // Cancel and delete the generation synchronously via the backend
        await podcastGeneration.cancel(podcastId);

        // Force immediate refresh of the job list to remove the cancelled job
        await podcastJobs.refetch();

        toast({
          title: "Generation Cancelled",
          description: "Podcast generation has been cancelled and removed"
        });
      } else {
        // Delete the completed podcast
        await deletePodcastMutation.mutateAsync(podcastId);
        toast({
          title: "Podcast Deleted",
          description: "The podcast has been deleted successfully"
        });
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      const actionText = isGenerating ? 'cancel' : 'delete';
      toast({
        title: `${actionText === 'cancel' ? 'Cancel' : 'Delete'} Failed`,
        description: `Failed to ${actionText} podcast: ${errorMessage}`,
        variant: "destructive"
      });
    }
  }, [deletePodcastMutation, selectedFile, toast, podcastGeneration]);

  const handleSaveFile = useCallback(async (content: string) => {
    if (!selectedFile) return;

    try {
      const fileId = selectedFile.id;
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
    <div className="flex flex-col h-full relative">
      {/* ====== SINGLE RESPONSIBILITY: Header rendering ====== */}
      <div className={`${PANEL_HEADERS.container} fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-200`}>
        <div className={PANEL_HEADERS.layout}>
          <div className={PANEL_HEADERS.titleContainer}>
            <div className={PANEL_HEADERS.iconContainer}>
              <Palette className={PANEL_HEADERS.icon} />
            </div>
            <h3 className={PANEL_HEADERS.title}>
              {isReportPreview ? 'Studio/Report' : 'Studio'}
            </h3>
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
        <div className="flex-1 flex flex-col overflow-hidden pt-16">
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
                      const itemId = item.id || index.toString();

                      if (item.type === 'report') {
                        // Check if this report is currently being generated
                        const isGenerating = item.status === 'running' || item.status === 'pending' ||
                                            (reportGeneration.activeJob && reportGeneration.activeJob.jobId === item.id);

                        const sourceCount = getSourceCount(item);
                        const timeAgo = getRelativeTime(item.created_at);

                        return (
                          <div
                            key={`report-${itemId}`}
                            className="relative rounded-xl transition-all duration-300 cursor-pointer group border overflow-hidden bg-white hover:bg-gray-50 border-gray-200 hover:border-gray-300 hover:shadow-md"
                            onClick={() => handleSelectReport(item)}
                          >
                            {/* Highlight sweep for generating state */}
                            {isGenerating && (
                              <div className="absolute inset-0 bg-gradient-to-r from-blue-50/80 via-blue-100/60 to-blue-50/80">
                                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-blue-200/40 to-transparent animate-sweep"></div>
                              </div>
                            )}

                            <div className="relative z-10 p-3">
                              <div className="flex items-start justify-between">
                                <div className="flex items-start space-x-3 flex-1 min-w-0">
                                  {/* Report Icon */}
                                  <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-emerald-500 group-hover:bg-emerald-600 shadow-sm">
                                    <BookOpen className="h-4 w-4 text-white" />
                                  </div>

                                  {/* Content */}
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center space-x-2 mb-1">
                                      <h4 className="text-sm font-semibold truncate text-gray-900 group-hover:text-emerald-800">
                                        {item.title || item.article_title || 'Research Report'}
                                      </h4>
                                      {isGenerating && (
                                        <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                                          <div className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-ping mr-1"></div>
                                          Generating
                                        </span>
                                      )}
                                    </div>

                                    {/* Preview text */}
                                    <p className="text-xs text-gray-600 leading-relaxed mb-2 line-clamp-1">
                                      {isGenerating
                                        ? (item.progress || reportGeneration.progress || 'Analyzing sources and generating insights...')
                                        : getReportPreview(item)
                                      }
                                    </p>

                                    {/* Metadata */}
                                    <div className="flex items-center text-xs space-x-3">
                                      <div className="flex items-center text-gray-500">
                                        <Clock className="h-3 w-3 mr-1" />
                                        <span>{timeAgo}</span>
                                      </div>
                                      <div className="flex items-center text-gray-500">
                                        <Database className="h-3 w-3 mr-1" />
                                        <span>{sourceCount} sources</span>
                                      </div>
                                    </div>
                                  </div>
                                </div>

                                {/* Actions */}
                                <div className={`transition-opacity ${
                                  isGenerating ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                                }`}>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 w-7 p-0 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleDeleteReport(item);
                                    }}
                                  >
                                    <Trash2 className="h-3.5 w-3.5" />
                                  </Button>
                                </div>
                              </div>
                            </div>
                          </div>
                        );
                      } else if (item.type === 'podcast') {
                        const isExpanded = expandedPodcasts.has(itemId);
                        // Check if this podcast is currently being generated
                        const isGenerating = item.status === 'running' || item.status === 'pending' ||
                                            (podcastGeneration.activeJob && podcastGeneration.activeJob.jobId === item.id);

                        const sourceCount = getSourceCount(item);
                        const timeAgo = getRelativeTime(item.created_at);

                        return (
                          <div
                            key={`podcast-${itemId}`}
                            className="relative rounded-xl border transition-all duration-300 overflow-hidden bg-white hover:bg-gray-50 border-gray-200 hover:border-gray-300 hover:shadow-md"
                          >
                            {/* Highlight sweep for generating state */}
                            {isGenerating && (
                              <div className="absolute inset-0 bg-gradient-to-r from-blue-50/80 via-blue-100/60 to-blue-50/80">
                                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-blue-200/40 to-transparent animate-sweep"></div>
                              </div>
                            )}

                            {/* Podcast Header */}
                            <div
                              className="p-3 cursor-pointer hover:bg-gray-50 transition-colors duration-200 group relative z-10"
                              onClick={() => handlePodcastClick(item)}
                            >
                              <div className="flex items-start justify-between">
                                <div className="flex items-start space-x-3 flex-1 min-w-0">
                                  {/* Podcast Icon */}
                                  <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-violet-500 group-hover:bg-violet-600 shadow-sm">
                                    {isExpanded ? (
                                      <ChevronDown className="h-4 w-4 text-white" />
                                    ) : (
                                      <Headphones className="h-4 w-4 text-white" />
                                    )}
                                  </div>

                                  {/* Content */}
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center space-x-2 mb-1">
                                      <h4 className="text-sm font-semibold truncate text-gray-900 group-hover:text-violet-800">
                                        {item.title || 'Panel Discussion'}
                                      </h4>
                                      {isGenerating && (
                                        <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                                          <div className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-ping mr-1"></div>
                                          Generating
                                        </span>
                                      )}
                                    </div>

                                    {/* Description/Progress */}
                                    {isGenerating && (item.progress || podcastGeneration.progress) && (
                                      <p className="text-xs text-blue-700 mb-2 font-medium">
                                        {item.progress || podcastGeneration.progress}
                                      </p>
                                    )}
                                    {!isGenerating && item.description && (
                                      <p className="text-xs text-gray-600 leading-relaxed mb-2 line-clamp-1">
                                        {item.description}
                                      </p>
                                    )}

                                    {/* Metadata */}
                                    <div className="flex items-center text-xs space-x-3">
                                      <div className="flex items-center text-gray-500">
                                        <Clock className="h-3 w-3 mr-1" />
                                        <span>{timeAgo}</span>
                                      </div>
                                      <div className="flex items-center text-gray-500">
                                        <Database className="h-3 w-3 mr-1" />
                                        <span>{sourceCount} sources</span>
                                      </div>
                                      <div className="flex items-center text-gray-500">
                                        <Users className="h-3 w-3 mr-1" />
                                        <span>{item.expert_names ? Object.keys(item.expert_names).length : 3} speakers</span>
                                      </div>
                                      <div className="flex items-center text-violet-600">
                                        <div className="w-1.5 h-1.5 bg-violet-500 rounded-full mr-1"></div>
                                        <span className="font-medium">Podcast</span>
                                      </div>
                                    </div>
                                  </div>
                                </div>

                                {/* Actions */}
                                <div className="flex items-center space-x-2">
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 w-7 p-0 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md opacity-0 group-hover:opacity-100 transition-opacity"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleDeletePodcast(item);
                                    }}
                                  >
                                    <Trash2 className="h-3.5 w-3.5" />
                                  </Button>
                                  <div className={`w-2 h-2 rounded-full transition-colors ${isExpanded ? 'bg-violet-400' : 'bg-gray-300'}`}></div>
                                </div>
                              </div>
                            </div>

                            {/* Expanded Audio Player */}
                            {isExpanded && (
                              <div className="border-t border-gray-100 bg-gray-50">
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
        <div className="flex-1 pt-16 overflow-hidden">
          {/* Report preview content when viewing a specific report */}
        </div>
      )}

      {/* ====== SINGLE RESPONSIBILITY: File viewer overlay ====== */}
      {selectedFile && (
        <div className="fixed inset-0 z-40 pt-16 overflow-hidden">
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
            hideHeader={isReportPreview}
            isPreviewingEdits={isPreviewingEdits}
          />
        </div>
      )}

    </div>
  );
};

export default StudioPanel;
