import React, { useState, useImperativeHandle, forwardRef, useEffect, useCallback, useMemo } from "react";
import { Trash2, Plus, ChevronLeft, RefreshCw, AlertCircle, Upload, Group, File as FileIcon, FileText, Music, Video, Presentation, Database, Link2, Globe } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useQueryClient } from '@tanstack/react-query';
import { Button } from "@/shared/components/ui/button";
import { Alert, AlertDescription } from "@/shared/components/ui/alert";
import { Badge } from "@/shared/components/ui/badge";
import sourceService from "@/features/notebook/services/SourceService";
import { PANEL_HEADERS, COLORS } from "@/features/notebook/config/uiConfig";
import { FileIcons } from "@/shared/types";
import { Source, SourcesListProps } from "@/features/notebook/type";
import { FileMetadata } from "@/shared/types";
import { useFileSelection } from "@/features/notebook/hooks/file/useFileSelection";
import { useParsedFiles, sourceKeys } from "@/features/notebook/hooks/sources/useSources";
import { useNotebookJobStream, JobEvent } from "@/shared/hooks/useNotebookJobStream";
import AddSourceModal from "./AddSourceModal";
import { SourceItem } from "./SourceItem";
import { useToast } from "@/shared/components/ui/use-toast";

const fileIcons: FileIcons = {
  pdf: FileIcon,
  txt: FileText,
  md: FileText, 
  ppt: Presentation,
  pptx: Presentation,
  docx: FileText,
  mp3: Music,
  mp4: Video,
  wav: Music,
  m4a: Music,
  avi: Video,
  mov: Video,
  mkv: Video,
  webm: Video,
  wmv: Video,
  m4v: Video,
  url: Link2,
  website: Globe,
  media: Video
};

// Define ref interface for the SourcesList component
interface SourcesListRef {
  getSelectedFiles: () => Source[];
  getSelectedSources: () => Source[];
  clearSelection: () => void;
  refreshSources: () => Promise<void>;
}

// Helper function to get principle file icon with visual indicator
  const getPrincipleFileIcon = (source: Source): React.ComponentType<any> => {
  // Enhanced URL detection with multiple fallbacks
  const isUrl = source.ext === 'url' || 
                source.metadata?.source_url || 
                source.metadata?.extraction_type === 'url_extractor' ||
                source.metadata?.processing_method === 'media' ||
                source.metadata?.processing_method === 'web_scraping_no_crawl4ai' ||
                source.metadata?.processing_method === 'crawl4ai_only' ||
                source.metadata?.file_extension === '.md' && source.metadata?.original_filename?.includes('_20');
  
  if (isUrl) {
    const processingType = source.metadata?.processing_method || source.metadata?.processing_type;
    return processingType === 'media' ? (fileIcons.media ?? FileIcon) : (fileIcons.website ?? Globe);
  }
  
  // For regular files, use the file extension
  const icon = fileIcons[source.ext || 'unknown'];
  return icon ?? FileIcon;
};


const SourcesList = forwardRef<SourcesListRef, SourcesListProps>(({ notebookId, onSelectionChange, onToggleCollapse, onOpenModal, onCloseModal }, ref) => {
  const { toast } = useToast();
  // ✅ TanStack Query as single source of truth
  const {
    data: parsedFilesResponse,
    isLoading,
    error: queryError,
    refetch: refetchFiles
  } = useParsedFiles(notebookId);

  // Query client for manual invalidation
  const queryClient = useQueryClient();

  // ✅ Use Set for efficient selection management
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const queryErrorMessage = queryError?.message || null;

  // Group state
  const [isGrouped, setIsGrouped] = useState(false);

  // Keep a minimal local map of in-flight items; render as normal SourceItem and update in-place
  const [localUploads, setLocalUploads] = useState<Record<string, Source>>({});

  // Helper to build a stable key - use file_id directly
  const keyForSource = useCallback((s: Source) => {
    // Use file_id as the key (database primary key)
    return s.file_id || s.id || `source-${s.id}`;
  }, []);

  // Handle backend completion signals - MUST be defined before SSE hook
  const handleProcessingComplete = useCallback((fileId: string) => {
    console.log('[SourcesList] handleProcessingComplete called with fileId:', fileId);

    // Use the real database file_id to remove local placeholder
    setLocalUploads(prev => {
      // Find which local upload corresponds to this file_id
      const entryToRemove = Object.entries(prev).find(([_, source]) => source.file_id === fileId);

      if (entryToRemove) {
        const [key] = entryToRemove;
        console.log('[SourcesList] Found and removing local upload by file_id:', key);
        const next = { ...prev };
        delete next[key];
        return next;
      }

      console.log('[SourcesList] ⚠️ No local upload found with file_id:', fileId);
      return prev;
    });

    // Refetch to get the completed item from server
    refetchFiles();
  }, [refetchFiles]);

  // ✅ Real-time updates via SSE
  useNotebookJobStream({
    notebookId,
    enabled: true, // Keep SSE connection active while list is mounted
    onJobEvent: useCallback((event: JobEvent) => {
      // Handle source events (file/URL processing updates)
      if (event.entity === 'source') {
        console.log('[SourcesList] Source event received:', event);

        if (event.status === 'SUCCESS') {
          console.log('[SourcesList] SUCCESS event - using database file_id:', event.id);
          // Use the database ID (knowledge base item primary key) to match
          handleProcessingComplete(event.id);
        } else {
          // For other events (like FAILURE or intermediate progress), update the local item directly
          // and also trigger a background refetch without waiting for it.
          queryClient.invalidateQueries({ queryKey: sourceKeys.parsedFiles(notebookId) });

          if (event.status === 'FAILURE') {
            const name = event.payload?.title || event.payload?.filename || 'Source';
            const description = event.payload?.error || 'Upload failed';
            toast({ title: `${name} failed`, description, variant: 'destructive' });
            // Stop tracking placeholder on failure using file_id
            const fileId = event.id;
            if (fileId) {
              console.log('[SourcesList] Marking failed upload:', fileId);
              // Mark local upload item as failed (keep visible if server doesn't return an item)
              setLocalUploads(prev => {
                const existing = prev[fileId];
                if (!existing) return prev;
                return { ...prev, [fileId]: { ...existing, parsing_status: 'failed' } };
              });
            }
          } else {
            // Intermediate updates: propagate parsing_status if present using file_id
            const fileId = event.id;
            if (fileId && event.payload?.parsing_status) {
              const status = event.payload.parsing_status;
              setLocalUploads(prev => {
                const existing = prev[fileId];
                if (!existing) return prev;
                if (existing.parsing_status === status) return prev;
                return { ...prev, [fileId]: { ...existing, parsing_status: status } };
              });
            }
          }
        }
      }
    }, [queryClient, notebookId, toast, handleProcessingComplete]),
    onConnected: useCallback(() => {
      console.log('[SourcesList] SSE connected, syncing state');
      // Sync state when connection is established (handles missed events during disconnect)
      refetchFiles();
    }, [refetchFiles]),
  });

  // Integrate file selection hook by passing the ref to this component
  const {
    updateSelectedFiles
  } = useFileSelection(ref as any);
  
  // Set notebook ID for upload tracking
  useEffect(() => {
    // Sync list on mount and when notebook changes
    refetchFiles();
  }, [notebookId, refetchFiles]);

  // Get original filename from metadata
  const getOriginalFilename = (metadata: FileMetadata) => {
    return metadata.original_filename ||
           metadata.metadata?.original_filename ||
           metadata.metadata?.filename ||
           metadata.filename ||
           metadata.title ||
           'Unknown File';
  };

  // Get principle file extension
  const getPrincipleFileExtension = (metadata: FileMetadata) => {
    // Enhanced URL detection with multiple fallbacks
    const isUrl = metadata.source_url ||
                  metadata.extraction_type === 'url_extractor' ||
                  metadata.processing_method === 'media' ||
                  metadata.processing_method === 'web_scraping_no_crawl4ai' ||
                  metadata.processing_method === 'crawl4ai_only' ||
                  metadata.file_extension === '.md' && metadata.original_filename?.includes('_20');

    if (isUrl) {
      return 'url';
    }

    // Use original file extension, fallback to processed extension
    let originalExt = "unknown";
    if (metadata.file_extension) {
      originalExt = metadata.file_extension.startsWith('.') ?
                   metadata.file_extension.substring(1) :
                   metadata.file_extension;
    } else if (metadata.metadata?.file_extension) {
      originalExt = metadata.metadata.file_extension.startsWith('.') ?
                   metadata.metadata.file_extension.substring(1) :
                   metadata.metadata.file_extension;
    } else if (metadata.original_filename) {
      const parts = metadata.original_filename.split('.');
      if (parts.length > 1) {
        originalExt = parts.pop() || 'unknown';
      }
    } else if (metadata.metadata?.filename) {
      const parts = metadata.metadata.filename.split('.');
      if (parts.length > 1) {
        originalExt = parts.pop() || 'unknown';
      }
    }

    return originalExt.toLowerCase();
  };

  // Extract domain from URL for display
  const getDomainFromUrl = (url: string) => {
    try {
      const urlObj = new URL(url);
      return urlObj.hostname.replace('www.', '');
    } catch {
      return 'unknown';
    }
  };

  // Generate principle title for sources
  const generatePrincipleTitle = (metadata: FileMetadata) => {
    const isUrl = metadata.source_url ||
                  metadata.extraction_type === 'url_extractor' ||
                  metadata.processing_method === 'media' ||
                  metadata.processing_method === 'web_scraping_no_crawl4ai' ||
                  metadata.processing_method === 'crawl4ai_only' ||
                  metadata.file_extension === '.md' && metadata.original_filename?.includes('_20');

    if (isUrl) {
      const domain = metadata.source_url ? getDomainFromUrl(metadata.source_url) : 'Unknown Domain';
      const title = metadata.title || metadata.metadata?.title || 'Untitled';
      return `${domain} - ${title}`;
    }

    return getOriginalFilename(metadata);
  };

  // Get principle file info for sources
  const getPrincipleFileInfo = (metadata: FileMetadata) => {
    return {
      original_filename: getOriginalFilename(metadata),
      file_extension: getPrincipleFileExtension(metadata),
      file_size: metadata.file_size || metadata.metadata?.file_size,
      content_length: metadata.content_length || metadata.metadata?.content_length,
      source_url: metadata.source_url,
      processing_method: metadata.processing_method || metadata.processing_type
    };
  };

  // ✅ Derive sources directly from TanStack Query data with selection state
  const sources = useMemo(() => {
    if (!parsedFilesResponse?.results) {
      return [];
    }

    const data = parsedFilesResponse.results || [];

    return data.map((metadata: FileMetadata) => ({
      id: metadata.id || 'unknown',
      name: generatePrincipleTitle(metadata),
      title: generatePrincipleTitle(metadata),
      authors: '',
      ext: getPrincipleFileExtension(metadata),
      selected: selectedIds.has(metadata.id || ''),  // ✅ Derive selection from Set
      type: "parsed" as const,
      createdAt: metadata.upload_timestamp || new Date().toISOString(),
      file_id: metadata.id,
      upload_file_id: metadata.upload_file_id,
      parsing_status: metadata.parsing_status,
      ragflow_processing_status: (metadata as any).ragflow_processing_status,
      captioning_status: metadata.captioning_status,
      metadata: {
        ...metadata,
        file_extension: metadata.file_extension || getPrincipleFileExtension(metadata),
        knowledge_item_id: metadata.id || metadata.knowledge_item_id
      },
      error_message: metadata.error_message,
      originalFile: getPrincipleFileInfo(metadata)
    }));
  }, [parsedFilesResponse, selectedIds]);

  // No enrichment merge: local upload items are removed on success to avoid duplicates

  // Calculate selected count
  const selectedCount = sources.filter((source: Source) => source.selected).length;

  // Group sources by file type
  const groupSources = useCallback((sourcesToGroup: Source[]) => {
    const grouped = sourcesToGroup.reduce((acc: Record<string, Source[]>, source) => {
      const type = source.ext || 'unknown';
      if (!acc[type]) {
        acc[type] = [];
      }
      acc[type].push(source);
      return acc;
    }, {} as Record<string, Source[]>);

    // Sort groups by type name
    const sortedGroups = Object.keys(grouped)
      .sort()
      .reduce((acc: Record<string, Source[]>, type: string) => {
        acc[type] = grouped[type] || [];
        return acc;
      }, {} as Record<string, Source[]>);

    return sortedGroups;
  }, []);

  // Get processed sources (grouped or not); render local uploading items first, then server sources excluding duplicates
  const processedSources = useMemo(() => {
    const localItems = Object.values(localUploads);
    // Use file_id (real database ID) for matching - keys in localUploads ARE the file_ids
    const localFileIds = new Set(Object.keys(localUploads));

    // Debug logging
    if (localItems.length > 0) {
      console.log('[SourcesList] Deduplication check:', {
        localItemCount: localItems.length,
        localFileIds: Array.from(localFileIds),
        serverItemCount: sources.length,
      });
    }

    const serverItems = (sources as Source[]).filter((s) => {
      // Simple deduplication: if server item's file_id exists in local placeholders, filter it out
      const serverFileId = String(s.file_id || s.id);

      // Debug: ALWAYS log each server item when local items exist
      if (localItems.length > 0) {
        const matched = localFileIds.has(serverFileId);
        console.log('[SourcesList] Checking server item:', {
          title: s.title,
          file_id: serverFileId,
          matched,
          ragflow_status: s.ragflow_processing_status,
          parsing_status: s.parsing_status,
        });
        if (matched) {
          console.log('[SourcesList] 🔴 Server item FILTERED OUT due to file_id match');
          return false;
        }
      }

      // Filter out if file_id matches
      return !localFileIds.has(serverFileId);
    });

    if (localItems.length > 0) {
      console.log('[SourcesList] After deduplication:', {
        localItemsRendered: localItems.length,
        serverItemsRendered: serverItems.length,
        totalRendered: localItems.length + serverItems.length,
      });
    }

    const flatList = [...localItems, ...serverItems];
    if (isGrouped) {
      const grouped = groupSources(flatList);
      return grouped || {};
    }
    return flatList;
  }, [localUploads, sources, isGrouped, groupSources]);

  // Handle group toggle
  const handleGroupToggle = () => {
    setIsGrouped(prev => !prev);
  };

  // Expose methods to parent components
  useImperativeHandle(ref, (): SourcesListRef => ({
    getSelectedFiles: () => {
      return sources.filter((source: Source) =>
        source.selected &&
        (source.file_id || source.file)
      );
    },
    getSelectedSources: () => {
      return sources.filter((source: Source) => source.selected);
    },
    clearSelection: () => {
      setSelectedIds(new Set());  // ✅ Clear Set
      setTimeout(() => updateSelectedFiles(), 0);
    },
    refreshSources: async () => { await refetchFiles(); }
  }));

  // ✅ Toggle selection using Set
  const toggleSource = useCallback((id: string | number) => {
    setSelectedIds((prev) => {
      const newSet = new Set(prev);
      const strId = String(id);
      if (newSet.has(strId)) {
        newSet.delete(strId);
      } else {
        newSet.add(strId);
      }
      return newSet;
    });
    setTimeout(() => updateSelectedFiles(), 0);
  }, [updateSelectedFiles]);

  // Handle selection change notifications
  const selectedIdsString = useMemo(() => Array.from(selectedIds).join(','), [selectedIds]);

  useEffect(() => {
    if (onSelectionChange) {
      const timer = setTimeout(() => onSelectionChange(), 50);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [selectedIdsString, onSelectionChange]);

  // ✅ Optimistic delete for selected sources
  const handleDeleteSelected = async (): Promise<void> => {
    const selectedSources = sources.filter((source: Source) => source.selected);

    if (selectedSources.length === 0) {
      return;
    }

    // Clear selection immediately
    setSelectedIds(new Set());
    if (onSelectionChange) {
      setTimeout(() => onSelectionChange(), 0);
    }

    // Build a set of IDs to delete
    const idsToDelete = new Set<string>(
      selectedSources
        .map((s: Source) => s?.metadata?.knowledge_item_id)
        .filter((id: any): id is string => Boolean(id))
    );

    if (idsToDelete.size === 0) {
      return;
    }

    // Optimistically update cache
    const queryKey = sourceKeys.parsedFiles(notebookId);
    const previous = queryClient.getQueryData(queryKey) as any;

    queryClient.setQueryData(queryKey, (old: any) => {
      if (!old) return old;
      const oldResults = Array.isArray(old.results) ? old.results : [];
      const filtered = oldResults.filter((item: any) => !idsToDelete.has(String(item?.id)));

      // Try to maintain pagination count if present
      let next: any = { ...old, results: filtered };
      const prevCount = old?.meta?.pagination?.count ?? old?.count;
      if (typeof prevCount === 'number') {
        const delta = oldResults.length - filtered.length;
        if (old?.meta?.pagination) {
          next = {
            ...next,
            meta: {
              ...old.meta,
              pagination: { ...old.meta.pagination, count: Math.max(0, prevCount - delta) },
            },
          };
        } else {
          next = { ...next, count: Math.max(0, prevCount - delta) };
        }
      }
      return next;
    });

    try {
      // Execute deletions in parallel
      const results = await Promise.allSettled(
        Array.from(idsToDelete).map((id: string) => sourceService.deleteParsedFile(id, notebookId))
      );

      const failed: Source[] = [];
      results.forEach((res, idx) => {
        if (res.status === 'rejected') {
          failed.push(selectedSources[idx]);
        } else {
          const value: any = res.value;
          const ok = value?.success === true || (value && typeof value === 'object' && !value.error);
          if (!ok) {
            failed.push(selectedSources[idx]);
          }
        }
      });

      if (failed.length > 0) {
        // Rollback optimistic update and surface error
        queryClient.setQueryData(queryKey, previous);
        setError(`Failed to delete ${failed.length} file(s): ${failed.map((f) => f.title).join(', ')}`);
        setSelectedIds(new Set(failed.map((f) => String(f.id))));
        if (onSelectionChange) {
          setTimeout(() => onSelectionChange(), 100);
        }
      } else {
        // Keep optimistic state but refetch to sync
        queryClient.invalidateQueries({ queryKey });
      }
    } catch (e) {
      // Generic rollback on unexpected error
      queryClient.setQueryData(queryKey, previous);
      setError('Failed to delete selected files');
      setSelectedIds(new Set(selectedSources.map((f: Source) => String(f.id))));
      if (onSelectionChange) {
        setTimeout(() => onSelectionChange(), 100);
      }
    }
  };


  // ✅ Simplified - SSE handles real-time updates for new files
  const handleAddSource = (): void => {
    if (onOpenModal) {
      const modalContent = (
        <AddSourceModal
          onClose={() => onCloseModal?.('addSourceModal')}
          notebookId={notebookId}
          onSourcesAdded={() => {
            refetchFiles();
            if (onSelectionChange) {
              setTimeout(() => onSelectionChange(), 100);
            }
          }}
          onUploadStarted={(fileId: string, _filename: string, _fileType: string) => {
            // Record local upload placeholder with REAL database file_id
            console.log('[SourcesList] Creating local upload placeholder with real file_id:', fileId);

            setLocalUploads(prev => {
              // Derive ext
              const deriveExt = () => {
                if (_fileType === 'url') return 'url';
                if (_filename && typeof _filename === 'string') {
                  const parts = _filename.split('.');
                  if (parts.length > 1) return parts.pop()?.toLowerCase();
                }
                return undefined;
              };

              return {
                ...prev,
                [fileId]: {  // Use real file_id as key
                  id: fileId,
                  file_id: fileId,  // Store the REAL database file_id
                  title: _filename || 'Uploading…',
                  type: 'uploading',
                  selected: false,
                  parsing_status: 'uploading',
                  ext: deriveExt(),
                  metadata: {
                    processing_method: _fileType === 'url' ? 'url_extractor' : undefined,
                    original_filename: _filename,
                  },
                } as Source
              };
            });

            // Refetch to sync with server (server might have additional data)
            refetchFiles();
          }}
          onKnowledgeBaseItemsDeleted={() => {
            refetchFiles();
          }}
        />
      );
      onOpenModal('addSourceModal', modalContent);
    }
  };

  // Get tooltip text for source items
  const getSourceTooltip = (source: Source): string => {
    if (source.type === 'uploading' || source.parsing_status === 'uploading') {
      return 'Uploading…';
    }
    const isUrl = source.metadata?.source_url ||
                  source.metadata?.extraction_type === 'url_extractor' ||
                  source.metadata?.processing_method === 'media' ||
                  source.metadata?.processing_method === 'web_scraping_no_crawl4ai' ||
                  source.metadata?.processing_method === 'crawl4ai_only' ||
                  source.metadata?.file_extension === '.md' && source.metadata?.original_filename?.includes('_20');

    if (isUrl) {
      const originalUrl = source.originalFile?.sourceUrl ||
                         source.metadata?.source_url ||
                         (source.metadata?.original_filename?.includes('_20') ?
                           `https://${source.metadata.original_filename.match(/^([^_]+)/)?.[1] || 'unknown'}` :
                           'Unknown URL');
      return `Original URL: ${originalUrl}`;
    }
    return `Original file: ${source.originalFile?.filename || source.title || ''}`;
  };

  // Handle opening file preview
  const handlePreviewFile = (source: Source) => {
    if (!onOpenModal) {
      console.log('Modal system not available, preview requested for source:', source.title);
      return;
    }

    // Import FilePreview component dynamically
    import("@/features/notebook/components/shared/FilePreview").then(({ default: FilePreview }) => {
      const previewContent = (
        <FilePreview
          source={{
            id: String(source.id),
            name: source.name || source.title || 'Unknown',
            type: source.type as 'file' | 'url' | 'text',
            createdAt: source.createdAt || new Date().toISOString(),
            content: source.content,
            url: source.url,
            metadata: source.metadata,
            selected: source.selected,
            file_id: source.file_id,
            title: source.title,
            ext: source.ext,
            ragflow_processing_status: source.ragflow_processing_status
          }}
          isOpen={true}
          onClose={() => onCloseModal?.('filePreview')}
          notebookId={notebookId}
          useMinIOUrls={true}
        />
      );
      onOpenModal('filePreview', previewContent);
    }).catch((error) => {
      console.error('Failed to load FilePreview component:', error);
    });
  };



  return (
    <div className={`h-full flex flex-col ${COLORS.panels.commonBackground} min-h-0`}>
      {/* Header */}
      <div className={`${PANEL_HEADERS.container} ${PANEL_HEADERS.separator} flex-shrink-0`}>
        <div className={PANEL_HEADERS.layout}>
          <div className={PANEL_HEADERS.titleContainer}>
            <div className={PANEL_HEADERS.iconContainer}>
              <Database className={PANEL_HEADERS.icon} />
            </div>
            <h3 className={PANEL_HEADERS.title}>Sources</h3>
          </div>
          <div className={PANEL_HEADERS.actionsContainer}>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs text-gray-500 hover:text-gray-700"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                handleGroupToggle();
              }}
            >
              <Group className="h-3 w-3 mr-1" />
              Group
            </Button>
            {onToggleCollapse && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 text-gray-400 hover:text-gray-600"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onToggleCollapse();
                }}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Add Source Button */}
      <div className="flex-shrink-0 px-4 py-3 bg-white flex justify-center">
        <Button
          variant="default"
          size="sm"
          className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-full transition-colors text-sm"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            handleAddSource();
          }}
          disabled={isLoading}
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Source
        </Button>
      </div>

      {/* Error Display with unified styling */}
      <AnimatePresence>
        {(error || queryErrorMessage) && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="flex-shrink-0 p-4 bg-white"
          >
            <Alert variant="destructive" className="border-red-200 bg-red-50">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-sm text-red-800">
                {error || queryErrorMessage}
                <Button
                  variant="ghost"
                  size="sm"
                  className="ml-2 h-6 px-2 text-red-600 hover:text-red-800"
                  onClick={() => setError(null)}
                >
                  Dismiss
                </Button>
              </AlertDescription>
            </Alert>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Simple Selection Bar */}
      {sources.length > 0 && (
        <div className="flex-shrink-0 px-4 py-3 bg-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs text-gray-500 hover:text-gray-700"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  const allSelected = sources.length > 0 && selectedCount === sources.length;
                  if (allSelected) {
                    setSelectedIds(new Set());  // ✅ Deselect all
                  } else {
                    setSelectedIds(new Set(sources.map((s: Source) => String(s.id))));  // ✅ Select all
                  }
                  setTimeout(() => updateSelectedFiles(), 0);
                }}
                disabled={sources.length === 0}
              >
                {sources.length > 0 && selectedCount === sources.length ? 'Deselect All' : 'Select All'}
              </Button>
            </div>
            
            <Button
              variant="ghost"
              size="sm"
              className={`h-6 px-2 text-xs transition-colors ${
                selectedCount > 0 
                  ? 'text-gray-500 hover:text-red-600' 
                  : 'text-gray-300 cursor-not-allowed'
              }`}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                if (selectedCount > 0) {
                  handleDeleteSelected();
                }
              }}
              disabled={selectedCount === 0}
            >
              <Trash2 className="h-3 w-3 mr-1" />
              Remove
            </Button>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 min-h-0 overflow-y-auto relative">
        {isGrouped ? (
          // Grouped rendering with unified styling
          <div>
            {Object.entries(processedSources as Record<string, Source[]>).map(([type, groupSources]: [string, Source[]]) => (
              <div key={type}>
                <div className="px-4 py-2 bg-white sticky top-0">
                  <div className="flex items-center space-x-2">
                    <div className="w-5 h-5 bg-gray-200 rounded-md flex items-center justify-center">
                      {React.createElement(fileIcons[type] || FileIcon, {
                        className: "h-3 w-3 text-gray-600"
                      })}
                    </div>
                    <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                      {type.toUpperCase()}
                    </h4>
                    <Badge variant="outline" className="text-xs bg-white border-gray-300">
                      {groupSources.length}
                    </Badge>
                  </div>
                </div>
                {groupSources.map((source: Source) => (
                  <SourceItem
                    key={keyForSource(source)}
                    source={source}
                    onToggle={toggleSource}
                    onPreview={() => handlePreviewFile(source)}
                    getSourceTooltip={getSourceTooltip}
                    getPrincipleFileIcon={getPrincipleFileIcon}
                  />
                ))}
              </div>
            ))}
          </div>
        ) : (
          // Ungrouped rendering with unified styling
          <div>
            {(processedSources as Source[]).map((source: Source) => (
              <SourceItem
                key={keyForSource(source)}
                source={source}
                onToggle={() => toggleSource(source.id)}
                onPreview={() => handlePreviewFile(source)}
                getSourceTooltip={getSourceTooltip}
                getPrincipleFileIcon={getPrincipleFileIcon}
              />
            ))}
          </div>
        )}
        
        {/* Empty/Loading States */}
        {!isLoading && sources.length === 0 && (
          <div className="p-8 text-center">
            <div className="w-12 h-12 bg-white rounded-lg mx-auto mb-3 flex items-center justify-center">
              <Upload className="h-6 w-6 text-gray-400" />
            </div>
            <h3 className="text-sm font-medium text-gray-900 mb-1">No files yet</h3>
            <p className="text-xs text-gray-500">Add files to get started</p>
          </div>
        )}
        
        {isLoading && sources.length === 0 && (
          <div className="p-8 text-center">
            <RefreshCw className="h-6 w-6 text-gray-400 animate-spin mx-auto mb-3" />
            <p className="text-sm text-gray-500">Loading...</p>
          </div>
        )}
      </div>

    </div>
  );
});

export default SourcesList;
