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
};

// ─── PARSED FILES ────────────────────────────────────────────────────────────

/**
 * Hook to fetch parsed files
 *
 * Real-time updates are handled via SSE in SourcesList component.
 * No polling - updates happen instantly when backend events are received.
 */
export const useParsedFiles = (
  notebookId: string,
  params?: { limit?: number; offset?: number }
) => {
  return useQuery({
    queryKey: sourceKeys.parsedFiles(notebookId, params),
    queryFn: () => sourceService.listParsedFiles(notebookId, params || {}),
    enabled: !!notebookId,
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes cache
    retry: 2,
    refetchOnWindowFocus: false,
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
// Note: Individual file status monitoring is now handled by useFileStatusSSE hook
// which uses SSE for real-time updates instead of polling

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
