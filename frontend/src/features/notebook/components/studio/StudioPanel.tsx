// ====== SOLID PRINCIPLES REFACTORED STUDIO PANEL ======
// This component demonstrates all 5 SOLID principles in action

import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Maximize2, Minimize2, Settings, Palette, Edit, Download, Save, X, Eye } from 'lucide-react';
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
import { useNotebookJobStream } from '@/shared/hooks/useNotebookJobStream';
import { useQueryClient } from '@tanstack/react-query';
import { studioKeys } from '@/features/notebook/hooks/studio/useStudio';

// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Import focused UI components
import ReportGenerationForm from './ReportGenerationForm';
import PodcastGenerationForm from './PodcastGenerationForm';
import PodcastAudioPlayer from './PodcastAudioPlayer';
import FileViewer from './FileViewer';
import StudioList from './list/StudioList';

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

// ====== UNIFIED STUDIO ITEMS ======
import { combineStudioItems } from '@/features/notebook/adapters/studioItemAdapter';
import type { ReportStudioItem, PodcastStudioItem } from '@/features/notebook/types/studioItem';

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
  const queryClient = useQueryClient();

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
      language: 'en',
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

  // ====== Real-time updates via SSE ======
  useNotebookJobStream({
    notebookId,
    enabled: !!notebookId,
    onConnected: (nbId) => {
      // Sync current state when SSE connection is established/re-established
      // This ensures we don't miss status changes that happened during page refresh
      console.log('[StudioPanel] SSE connected, syncing current state');
      queryClient.invalidateQueries({ queryKey: studioKeys.reportJobs(nbId) });
      queryClient.invalidateQueries({ queryKey: studioKeys.podcastJobs(nbId) });
    },
    onJobEvent: (event) => {
      if (!notebookId) return;
      if (event.entity === 'report') {
        queryClient.invalidateQueries({ queryKey: studioKeys.reportJobs(notebookId) });
      } else if (event.entity === 'podcast') {
        queryClient.invalidateQueries({ queryKey: studioKeys.podcastJobs(notebookId) });
      }
    },
  });


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

      // Download directly using browser navigation (avoids CORS issues)
      await studioService.downloadPodcastAudio(podcastId, notebookId);

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
    const isGenerating = (report.status === 'running' || report.status === 'pending') ||
                        (reportGeneration.activeJob && reportGeneration.activeJob.jobId === report.id &&
                         (reportGeneration.activeJob.status === 'running' || reportGeneration.activeJob.status === 'pending'));

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
        // Cancel and delete via backend
        await reportGeneration.cancel(reportId);
        toast({ title: "Report Cancelled", description: "Generation cancelled and removed" });
      } else {
        await deleteReportMutation.mutateAsync(reportId);
        toast({ title: "Report Deleted", description: "Deleted successfully" });
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
    const isGenerating = (podcast.status === 'running' || podcast.status === 'pending' || podcast.status === 'generating') ||
                        (podcastGeneration.activeJob && podcastGeneration.activeJob.jobId === podcast.id &&
                         (podcastGeneration.activeJob.status === 'running' || podcastGeneration.activeJob.status === 'pending'));

    const confirmMessage = isGenerating
      ? 'Are you sure you want to cancel and delete this podcast?'
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
        // Replicate report behavior: cancel running job; no explicit delete
        await podcastGeneration.cancel(podcastId);
        toast({ title: 'Podcast Cancelled', description: 'Generation cancelled' });
      } else {
        await deletePodcastMutation.mutateAsync(podcastId);
        toast({ title: 'Podcast Deleted', description: 'Deleted successfully' });
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      const actionText = isGenerating ? 'cancel' : 'delete';
      toast({
        title: `${actionText === 'cancel' ? 'Cancel' : 'Delete'} Failed`,
        description: `Failed to ${actionText} podcast: ${errorMessage}`,
        variant: 'destructive'
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
      <div className={PANEL_HEADERS.container}>
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
          <div className="flex-shrink-0 p-4 bg-gray-50/50 border-b border-gray-200/60">
            {/* ====== LISKOV SUBSTITUTION PRINCIPLE (LSP) ====== */}
            {/* Both forms follow the same interface contract */}
            <div className="grid grid-cols-2 gap-4">
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
          </div>

          {/* ====== SCROLLABLE SECTION: Generated Files List ====== */}
          <div className="flex-1 overflow-auto scrollbar-overlay">
            <StudioList
              items={combineStudioItems(reportJobs.jobs, podcastJobs.jobs)}
              isLoading={reportJobs.isLoading || podcastJobs.isLoading}
              error={reportJobs.error || podcastJobs.error}
              notebookId={notebookId}
              expandedPodcasts={expandedPodcasts}
              onSelectReport={(item: ReportStudioItem) => {
                // Find original report from jobs to pass to handler
                const originalReport = reportJobs.jobs.find((r: ReportItem) => r.id === item.id);
                if (originalReport) handleSelectReport(originalReport);
              }}
              onDeleteReport={(item: ReportStudioItem) => {
                const originalReport = reportJobs.jobs.find((r: ReportItem) => r.id === item.id);
                if (originalReport) handleDeleteReport(originalReport);
              }}
              onTogglePodcast={(item: PodcastStudioItem) => {
                const originalPodcast = podcastJobs.jobs.find((p: PodcastItem) => p.id === item.id);
                if (originalPodcast) handlePodcastClick(originalPodcast);
              }}
              onDeletePodcast={(item: PodcastStudioItem) => {
                const originalPodcast = podcastJobs.jobs.find((p: PodcastItem) => p.id === item.id);
                if (originalPodcast) handleDeletePodcast(originalPodcast);
              }}
              onDownloadPodcast={(item: PodcastStudioItem) => {
                const originalPodcast = podcastJobs.jobs.find((p: PodcastItem) => p.id === item.id);
                if (originalPodcast) handleDownloadPodcast(originalPodcast);
              }}
            />
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
