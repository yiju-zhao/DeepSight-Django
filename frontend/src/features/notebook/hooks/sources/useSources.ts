/**
 * TanStack Query-powered hooks for sources operations
 * Handles file listing, uploading, parsing, and management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import sourceService from '@/features/notebook/services/SourceService';

// Query keys factory
const sourceKeys = {
  all: ['sources'] as const,
  notebook: (notebookId: string) => [...sourceKeys.all, 'notebook', notebookId] as const,
  
  // Parsed files
  parsedFiles: (notebookId: string, params?: any) => 
    [...sourceKeys.notebook(notebookId), 'parsed-files', params] as const,
  
  // Knowledge base
  knowledgeBase: (notebookId: string, params?: any) => 
    [...sourceKeys.notebook(notebookId), 'knowledge-base', params] as const,
  
  // File status
  fileStatus: (notebookId: string, fileId: string) => 
    [...sourceKeys.notebook(notebookId), 'file-status', fileId] as const,
};

// ─── PARSED FILES ────────────────────────────────────────────────────────────

/**
 * Hook to fetch parsed files
 *
 * Polling is now disabled by default - real-time updates are handled via SSE.
 * Set polling: true in options if you need to force polling behavior (fallback).
 */
export const useParsedFiles = (
  notebookId: string,
  params?: { limit?: number; offset?: number },
  options?: { polling?: boolean }
) => {
  const enablePolling = options?.polling === true; // Default: false (SSE-driven)
  return useQuery({
    queryKey: sourceKeys.parsedFiles(notebookId, params),
    queryFn: () => sourceService.listParsedFiles(notebookId, params || {}),
    enabled: !!notebookId,
    staleTime: 30 * 1000, // 30 seconds - files can change when processing completes
    gcTime: 5 * 60 * 1000, // 5 minutes cache
    retry: 2,
    refetchOnWindowFocus: false,
    // Polling disabled by default (SSE handles real-time updates)
    refetchInterval: enablePolling ? (query) => {
      // Check if any files are being processed
      const data = query?.state?.data;
      if (!data?.results) return false;

      const hasProcessingFiles = data.results.some((file: any) => {
        const isParsingInProgress = file.parsing_status &&
          ['queueing', 'uploading', 'parsing', 'captioning'].includes(file.parsing_status);
        const isRagflowInProgress = file.ragflow_processing_status &&
          ['pending', 'uploading', 'parsing'].includes(file.ragflow_processing_status);
        const isCaptioningInProgress = file.captioning_status &&
          ['pending', 'in_progress'].includes(file.captioning_status);

        return isParsingInProgress || isRagflowInProgress || isCaptioningInProgress;
      });

      // Use exponential backoff: 3s initially, then 5s, then stop when nothing is processing
      if (hasProcessingFiles) {
        const attemptIndex = query?.state?.fetchFailureCount || 0;
        return attemptIndex < 5 ? 3000 : 5000;
      }

      return false; // Stop polling when nothing is processing
    } : false,
  });
};

// ─── KNOWLEDGE BASE ──────────────────────────────────────────────────────────

export const useKnowledgeBase = (notebookId: string, params?: { limit?: number; offset?: number; content_type?: string }) => {
  return useQuery({
    queryKey: sourceKeys.knowledgeBase(notebookId, params),
    queryFn: () => sourceService.getKnowledgeBase(notebookId, params || {}),
    enabled: !!notebookId,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes cache
    retry: 1,
  });
};

// ─── FILE STATUS ─────────────────────────────────────────────────────────────

/**
 * Hook to fetch individual file status with intelligent polling
 * Uses exponential backoff and stops when processing is complete
 */
export const useFileStatus = (notebookId: string, fileId: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: sourceKeys.fileStatus(notebookId, fileId),
    queryFn: () => sourceService.getStatus(fileId, notebookId),
    enabled: !!notebookId && !!fileId && enabled,
    staleTime: 5 * 1000, // 5 seconds - status changes frequently during processing
    gcTime: 60 * 1000, // 1 minute cache
    retry: 3,
    refetchInterval: (query) => {
      const data = query?.state?.data;
      if (!data) return false;

      // Check if any processing is happening
      const isParsingInProgress = data.parsing_status &&
        ['queueing', 'uploading', 'parsing', 'captioning'].includes(data.parsing_status);
      const isRagflowInProgress = data.ragflow_processing_status &&
        ['pending', 'uploading', 'parsing'].includes(data.ragflow_processing_status);
      const isCaptioningInProgress = data.captioning_status &&
        ['pending', 'in_progress'].includes(data.captioning_status);

      // Stop polling if everything is done or failed
      if (!isParsingInProgress && !isRagflowInProgress && !isCaptioningInProgress) {
        return false;
      }

      // Use exponential backoff: start at 2s, then 3s, then 5s
      const dataUpdatedAt = query?.state?.dataUpdatedAt || 0;
      const now = Date.now();
      const timeSinceLastUpdate = now - dataUpdatedAt;

      if (timeSinceLastUpdate < 10000) {
        return 2000; // First 10 seconds: poll every 2s
      } else if (timeSinceLastUpdate < 30000) {
        return 3000; // 10-30 seconds: poll every 3s
      } else {
        return 5000; // After 30 seconds: poll every 5s
      }
    }
  });
};

// ─── MUTATIONS ───────────────────────────────────────────────────────────────

export const useParseFile = (notebookId: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ file, uploadFileId }: { file: File | File[]; uploadFileId: string }) => 
      sourceService.parseFile(file, uploadFileId, notebookId),
    onSuccess: () => {
      // Invalidate parsed files to show the new file
      queryClient.invalidateQueries({
        queryKey: sourceKeys.parsedFiles(notebookId),
      });
    },
  });
};

export const useParseUrl = (notebookId: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ url, searchMethod, uploadFileId }: { 
      url: string | string[]; 
      searchMethod?: string; 
      uploadFileId?: string | null 
    }) => sourceService.parseUrl(url, notebookId, searchMethod || 'cosine', uploadFileId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: sourceKeys.parsedFiles(notebookId),
      });
    },
  });
};

export const useParseUrlWithMedia = (notebookId: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ url, searchMethod, uploadFileId }: { 
      url: string | string[]; 
      searchMethod?: string; 
      uploadFileId?: string | null 
    }) => sourceService.parseUrlWithMedia(url, notebookId, searchMethod || 'cosine', uploadFileId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: sourceKeys.parsedFiles(notebookId),
      });
    },
  });
};

export const useDeleteParsedFile = (notebookId: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (fileId: string) => sourceService.deleteParsedFile(fileId, notebookId),
    onSuccess: () => {
      // Invalidate parsed files to remove the deleted file
      queryClient.invalidateQueries({
        queryKey: sourceKeys.parsedFiles(notebookId),
      });
    },
  });
};

export const useDeleteFileByUploadId = (notebookId: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (uploadFileId: string) => sourceService.deleteFileByUploadId(uploadFileId, notebookId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: sourceKeys.parsedFiles(notebookId),
      });
    },
  });
};

export const useLinkKnowledgeBaseItem = (notebookId: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ knowledgeBaseItemId, notes }: { knowledgeBaseItemId: string; notes?: string }) => 
      sourceService.linkKnowledgeBaseItem(notebookId, knowledgeBaseItemId, notes || ''),
    onSuccess: () => {
      // Invalidate both parsed files and knowledge base
      queryClient.invalidateQueries({
        queryKey: sourceKeys.parsedFiles(notebookId),
      });
      queryClient.invalidateQueries({
        queryKey: sourceKeys.knowledgeBase(notebookId),
      });
    },
  });
};

export const useDeleteKnowledgeBaseItem = (notebookId: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (knowledgeBaseItemId: string) => 
      sourceService.deleteKnowledgeBaseItem(notebookId, knowledgeBaseItemId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: sourceKeys.knowledgeBase(notebookId),
      });
    },
  });
};

// ─── CONVENIENCE HOOKS ───────────────────────────────────────────────────────

/**
 * Combined hook for all source operations in one place
 * Useful for components that need multiple source operations
 */
export const useSourcesOperations = (notebookId: string) => {
  const parsedFiles = useParsedFiles(notebookId);
  const knowledgeBase = useKnowledgeBase(notebookId);
  
  const parseFile = useParseFile(notebookId);
  const parseUrl = useParseUrl(notebookId);
  const parseUrlWithMedia = useParseUrlWithMedia(notebookId);
  
  const deleteParsedFile = useDeleteParsedFile(notebookId);
  const deleteFileByUploadId = useDeleteFileByUploadId(notebookId);
  const linkKnowledgeBaseItem = useLinkKnowledgeBaseItem(notebookId);
  const deleteKnowledgeBaseItem = useDeleteKnowledgeBaseItem(notebookId);

  return {
    // Queries
    parsedFiles,
    knowledgeBase,
    
    // Mutations
    parseFile,
    parseUrl,
    parseUrlWithMedia,
    deleteParsedFile,
    deleteFileByUploadId,
    linkKnowledgeBaseItem,
    deleteKnowledgeBaseItem,
    
    // Convenience methods
    refreshSources: () => {
      parsedFiles.refetch();
      knowledgeBase.refetch();
    }
  };
};

// Export query keys for external use
export { sourceKeys };
