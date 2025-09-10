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

export const useParsedFiles = (notebookId: string, params?: { limit?: number; offset?: number }) => {
  return useQuery({
    queryKey: sourceKeys.parsedFiles(notebookId, params),
    queryFn: () => sourceService.listParsedFiles(notebookId, params || {}),
    enabled: !!notebookId,
    staleTime: 30 * 1000, // 30 seconds - files can change when processing completes
    gcTime: 5 * 60 * 1000, // 5 minutes cache
    retry: 2,
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

export const useFileStatus = (notebookId: string, fileId: string) => {
  return useQuery({
    queryKey: sourceKeys.fileStatus(notebookId, fileId),
    queryFn: () => sourceService.getStatus(fileId, notebookId),
    enabled: !!notebookId && !!fileId,
    staleTime: 10 * 1000, // 10 seconds - status changes frequently during processing
    gcTime: 60 * 1000, // 1 minute cache
    retry: 3,
    refetchInterval: (query) => {
      // Auto-refetch every 2 seconds if still processing
      const status = query?.state?.data?.status;
      return status && ['pending', 'processing', 'in_progress', 'uploading'].includes(status) ? 2000 : false;
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