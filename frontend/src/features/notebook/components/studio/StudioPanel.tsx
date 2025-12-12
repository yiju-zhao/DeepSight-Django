// ====== SOLID PRINCIPLES REFACTORED STUDIO PANEL ======
// This component demonstrates all 5 SOLID principles in action

import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Maximize2, Minimize2, Settings, Palette, Edit, Download, Save, X, Eye, FileText } from 'lucide-react';
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
import { useNotebookSettings } from '@/features/notebook/contexts/NotebookSettingsContext';
import { useNotes } from '@/features/notebook/hooks/notes/useNotes';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/shared/components/ui/tabs';

// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Import focused UI components
import ReportGenerationForm from './ReportGenerationForm';
import PodcastGenerationForm from './PodcastGenerationForm';
import PodcastAudioPlayer from './PodcastAudioPlayer';
import FileViewer from './FileViewer';
import StudioList from './list/StudioList';
import NotesList from './NotesList';
import NoteViewer from './NoteViewer';

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
import { combineStudioItems, fromReports, fromPodcasts } from '@/features/notebook/adapters/studioItemAdapter';
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
  const { reportConfig, podcastConfig, updateReportConfig, updatePodcastConfig } = useNotebookSettings();

  // ====== SINGLE RESPONSIBILITY: UI State Management ======
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  const [selectedFileContent, setSelectedFileContent] = useState<string>('');
  const [viewMode, setViewMode] = useState<'preview' | 'edit'>('preview');
  const [isReportPreview, setIsReportPreview] = useState<boolean>(false);
  const [isPreviewingEdits, setIsPreviewingEdits] = useState<boolean>(false);
  const [expandedPodcasts, setExpandedPodcasts] = useState<Set<string>>(new Set());
  const [selectedPodcast, setSelectedPodcast] = useState<PodcastItem | null>(null);
  const [expandedByReport, setExpandedByReport] = useState<boolean>(false);

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
  const [selectedNoteId, setSelectedNoteId] = useState<number | null>(null);

  // ====== SINGLE RESPONSIBILITY: Notes Data ======
  const { notes } = useNotes(notebookId);

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
  // Initialize default configs - REMOVED (Handled in Context)
  // useEffect(() => {
  //   reportGeneration.updateConfig({ ... });
  //   podcastGeneration.updateConfig({ ... });
  // }, [reportGeneration.updateConfig, podcastGeneration.updateConfig]);

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
    // Note: Query invalidation is handled by useNotebookJobStream internally
    // to avoid duplicate invalidations that can cause race conditions
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
        ...reportConfig,
        ...configOverrides,
        source_ids: selectedFiles.map((f: FileItem) => f.id),
        model: configOverrides?.model || reportConfig.model || 'gpt-4'
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
  }, [reportGeneration.generate, reportConfig, selectedFiles, toast]);

  // ====== SINGLE RESPONSIBILITY: Podcast generation handler ======
  const handleGeneratePodcast = useCallback(async (configOverrides?: Partial<any>) => {
    try {
      const config = {
        ...podcastConfig,
        ...configOverrides,
        source_file_ids: selectedFiles.map((f: FileItem) => f.id),
        model: configOverrides?.model || podcastConfig.model || 'gpt-4'
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
  }, [podcastGeneration.generate, podcastConfig, selectedFiles, toast]);

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

      // Expand studio when opening report preview
      if (!isStudioExpanded && onToggleExpand) {
        onToggleExpand();
        setExpandedByReport(true);
      }
    } catch (error) {
      console.error('Failed to load report content:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      toast({
        title: "Error",
        description: "Failed to load report content: " + errorMessage,
        variant: "destructive"
      });
    }
  }, [studioService, notebookId, toast, isStudioExpanded, onToggleExpand]);

  const handlePodcastClick = useCallback((podcast: PodcastItem) => {
    // Set selected podcast for bottom player
    setSelectedPodcast(podcast);
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
    if (expandedByReport && onToggleExpand) {
      onToggleExpand();
      setExpandedByReport(false);
    }
  }, [expandedByReport, onToggleExpand]);

  const handlePreviewEdits = useCallback(() => {
    setIsPreviewingEdits(true);
    setViewMode('preview');
  }, []);

  // ====== OPEN/CLOSED PRINCIPLE (OCP) ======
  // Render method that can be extended without modification
  return (
    <div className="flex flex-col h-full relative">
      {/* ====== SINGLE RESPONSIBILITY: Header rendering ====== */}
      <div className={`${PANEL_HEADERS.container} ${PANEL_HEADERS.separator}`}>
        <div className={PANEL_HEADERS.layout}>
          <div className={PANEL_HEADERS.titleContainer}>
            {/* Icon removed per Huawei style guide */}
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
                    className="h-[32px] px-[12px] text-[12px] font-medium text-[#666666] hover:text-[#1E1E1E] hover:bg-[#F5F5F5] rounded-md transition-colors"
                    onClick={() => setViewMode('edit')}
                  >
                    <Edit className="h-3.5 w-3.5 mr-1.5" />
                    Edit
                  </Button>
                )}
                {viewMode === 'edit' && (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-[32px] px-[12px] text-[12px] font-medium text-[#666666] hover:text-[#1E1E1E] hover:bg-[#F5F5F5] rounded-md transition-colors"
                      onClick={handlePreviewEdits}
                    >
                      <Eye className="h-3.5 w-3.5 mr-1.5" />
                      Preview
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-[32px] px-[12px] text-[12px] font-medium text-[#666666] hover:text-[#1E1E1E] hover:bg-[#F5F5F5] rounded-md transition-colors"
                      onClick={() => handleSaveFile(selectedFileContent)}
                    >
                      <Save className="h-3.5 w-3.5 mr-1.5" />
                      Save
                    </Button>
                  </>
                )}
                {viewMode === 'preview' && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-[32px] px-[12px] text-[12px] font-medium text-[#666666] hover:text-[#1E1E1E] hover:bg-[#F5F5F5] rounded-md transition-colors"
                    onClick={() => handleDownloadReport(selectedFile)}
                  >
                    <Download className="h-3.5 w-3.5 mr-1.5" />
                    Download
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-[32px] w-[32px] p-0 text-[#B1B1B1] hover:text-[#666666] hover:bg-[#F5F5F5] rounded-md transition-colors"
                  onClick={toggleExpanded}
                >
                  {isStudioExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-[32px] w-[32px] p-0 text-[#B1B1B1] hover:text-[#666666] hover:bg-[#F5F5F5] rounded-md transition-colors"
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
                  className="h-[32px] px-[12px] text-[12px] font-medium text-[#666666] hover:text-[#1E1E1E] hover:bg-[#F5F5F5] rounded-md transition-colors"
                  onClick={handleRefresh}
                  disabled={reportJobs.isLoading || podcastJobs.isLoading || reportModels.isLoading}
                >
                  <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${reportJobs.isLoading || podcastJobs.isLoading || reportModels.isLoading ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>

                <Button
                  variant="ghost"
                  size="sm"
                  className="h-[32px] w-[32px] p-0 text-[#B1B1B1] hover:text-[#666666] hover:bg-[#F5F5F5] rounded-md transition-colors"
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
        <div className="flex-1 flex flex-col overflow-hidden bg-[#F5F5F5]">
          <Tabs defaultValue="reports" className="flex-1 flex flex-col min-h-0">
            <div className="bg-white border-b border-[#F7F7F7] px-6">
              <TabsList className="w-full justify-start h-12 p-0 bg-transparent border-0">
                <TabsTrigger
                  value="reports"
                  className="h-full rounded-none border-b-2 border-transparent data-[state=active]:border-[#CE0E2D] data-[state=active]:bg-transparent px-6"
                >
                  Reports
                </TabsTrigger>
                <TabsTrigger
                  value="podcasts"
                  className="h-full rounded-none border-b-2 border-transparent data-[state=active]:border-[#CE0E2D] data-[state=active]:bg-transparent px-6"
                >
                  Podcasts
                </TabsTrigger>
                <TabsTrigger
                  value="notes"
                  className="h-full rounded-none border-b-2 border-transparent data-[state=active]:border-[#CE0E2D] data-[state=active]:bg-transparent px-6 gap-2"
                >
                  <FileText className="h-4 w-4" />
                  Notes
                  {notes?.length > 0 && (
                    <span className="ml-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                      {notes.length}
                    </span>
                  )}
                </TabsTrigger>
              </TabsList>
            </div>

            {/* ====== REPORTS TAB ====== */}
            <TabsContent value="reports" className="flex-1 flex flex-col overflow-hidden mt-0 data-[state=inactive]:hidden">
              <div className="flex-shrink-0 px-6 py-6 bg-white border-b border-[#F7F7F7]">
                <ReportGenerationForm
                  config={reportConfig}
                  onConfigChange={updateReportConfig}
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
              </div>
              <div className="flex-1 overflow-auto scrollbar-overlay">
                <StudioList
                  items={fromReports(reportJobs.jobs)}
                  isLoading={reportJobs.isLoading}
                  error={reportJobs.error}
                  notebookId={notebookId}
                  expandedPodcasts={expandedPodcasts}
                  onSelectReport={(item: ReportStudioItem) => {
                    const originalReport = reportJobs.jobs.find((r: ReportItem) => r.id === item.id);
                    if (originalReport) handleSelectReport(originalReport);
                  }}
                  onDeleteReport={(item: ReportStudioItem) => {
                    const originalReport = reportJobs.jobs.find((r: ReportItem) => r.id === item.id);
                    if (originalReport) handleDeleteReport(originalReport);
                  }}
                  onTogglePodcast={() => { }}
                  onDeletePodcast={() => { }}
                  onDownloadPodcast={() => { }}
                />
              </div>
            </TabsContent>

            {/* ====== PODCASTS TAB ====== */}
            <TabsContent value="podcasts" className="flex-1 flex flex-col overflow-hidden mt-0 data-[state=inactive]:hidden">
              <div className="flex-shrink-0 px-6 py-6 bg-white border-b border-[#F7F7F7]">
                <PodcastGenerationForm
                  config={podcastConfig}
                  onConfigChange={updatePodcastConfig}
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
              <div className={`flex-1 overflow-auto scrollbar-overlay ${selectedPodcast && selectedPodcast.status === 'completed' ? 'pb-20' : ''}`}>
                <StudioList
                  items={fromPodcasts(podcastJobs.jobs)}
                  isLoading={podcastJobs.isLoading}
                  error={podcastJobs.error}
                  notebookId={notebookId}
                  expandedPodcasts={expandedPodcasts}
                  onSelectReport={() => { }}
                  onDeleteReport={() => { }}
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
              {/* Podcast Player within Tab */}
              {selectedPodcast && selectedPodcast.status === 'completed' && (
                <div className="flex-shrink-0 bg-white shadow-inner">
                  <PodcastAudioPlayer
                    podcast={{
                      id: selectedPodcast.id,
                      title: selectedPodcast.title || 'Untitled Podcast',
                      audio_url: (selectedPodcast as any).audio_url || selectedPodcast.audio_file || '',
                      duration: selectedPodcast.duration,
                      description: selectedPodcast.description || '',
                      status: selectedPodcast.status,
                      created_at: selectedPodcast.created_at || '',
                      updated_at: selectedPodcast.updated_at || ''
                    }}
                    notebookId={notebookId}
                    onDownload={() => handleDownloadPodcast(selectedPodcast)}
                    onClose={() => setSelectedPodcast(null)}
                  />
                </div>
              )}
            </TabsContent>

            {/* ====== NOTES TAB ====== */}
            <TabsContent value="notes" className="flex-1 flex flex-col overflow-hidden mt-0 relative data-[state=inactive]:hidden">
              {selectedNoteId ? (
                <NoteViewer
                  notebookId={notebookId}
                  noteId={selectedNoteId}
                  onClose={() => setSelectedNoteId(null)}
                />
              ) : (
                <NotesList
                  notebookId={notebookId}
                  onSelectNote={setSelectedNoteId}
                />
              )}
            </TabsContent>
          </Tabs>
        </div>
      ) : (
        <div className="flex-1 overflow-hidden">
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
              onDownload={() => handleDownloadReport(selectedFile)}
              onToggleExpand={toggleExpanded}
              onToggleViewMode={toggleViewMode}
              onContentChange={setSelectedFileContent}
              notebookId={notebookId}
              hideHeader={true}
              isPreviewingEdits={isPreviewingEdits}
            />
          )}
        </div>
      )}

      {/* File viewer is rendered inline when report preview is active */}

    </div>
  );
};

export default StudioPanel;
