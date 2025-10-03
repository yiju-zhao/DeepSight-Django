import React from 'react';
import { Loader2, AlertCircle, Image as ImageIcon } from 'lucide-react';
import { Source } from '@/features/notebook/type';

/**
 * Status rendering utilities for knowledge base items
 * Handles parsing status, RagFlow sync status, and captioning status
 */

export interface StatusIndicatorProps {
  source: Source;
}

/**
 * Renders the file processing status indicator
 * Shows different states: queueing, parsing, uploading, captioning, syncing, completed, failed
 */
export const renderFileStatus = (source: Source): React.ReactNode => {
  // Check parsing status
  const isFailed = source.parsing_status === 'failed' || source.parsing_status === 'error';

  // Check RagFlow status
  const ragflowProcessing = source.ragflow_processing_status &&
    ['uploading', 'parsing'].includes(source.ragflow_processing_status);
  const ragflowCompleted = source.ragflow_processing_status === 'completed';
  const ragflowFailed = source.ragflow_processing_status === 'failed';

  // Priority 1: Show parsing/upload errors
  if (isFailed) {
    return (
      <div className="flex items-center space-x-1">
        <AlertCircle className="h-3 w-3 text-red-500" />
        <span className="text-xs text-red-500">
          {source.parsing_status === 'error' ? 'Error' : 'Failed'}
        </span>
      </div>
    );
  }

  // Priority 2: Show completed status indicators (RagFlow sync + captions)
  return (
    <div className="flex items-center space-x-2">
      {/* RagFlow sync status */}
      {renderRagflowStatus(ragflowProcessing, ragflowCompleted, ragflowFailed)}

      {/* Image captions indicator */}
      {source.captioning_status === 'completed' && (
        <div className="flex items-center space-x-1" title="Images with captions available">
          <ImageIcon className="h-3 w-3 text-green-500" />
        </div>
      )}
    </div>
  );
};

/**
 * Renders RagFlow sync status indicator
 */
const renderRagflowStatus = (
  isProcessing: boolean,
  isCompleted: boolean,
  isFailed: boolean
): React.ReactNode => {
  if (isProcessing) {
    return (
      <div className="flex items-center space-x-1" title="Uploading to knowledge base...">
        <Loader2 className="h-3 w-3 text-blue-600 animate-spin" />
        <span className="text-xs text-gray-500">RAGFlowing...</span>
      </div>
    );
  }

  if (isCompleted) {
    return (
      <div className="flex items-center space-x-1" title="Successfully synced to knowledge base">
        <svg
          className="h-3 w-3 text-green-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <circle
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="2"
            fill="none"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M9 12l2 2 4-4"
          />
        </svg>
      </div>
    );
  }

  if (isFailed) {
    return (
      <div className="flex items-center space-x-1" title="Failed to sync to knowledge base">
        <AlertCircle className="h-3 w-3 text-orange-500" />
      </div>
    );
  }

  return null;
};

/**
 * Get human-readable text for processing status
 */
const getProcessingStatusText = (status?: string): string => {
  switch (status) {
    case 'uploading':
      return 'Uploading...';
    case 'parsing':
      return 'Parsing...';
    case 'queueing':
      return 'Queued...';
    case 'captioning':
      return 'Generating captions...';
    default:
      return 'Processing...';
  }
};

/**
 * Check if a source is currently being processed
 */
export const isSourceProcessing = (source: Source): boolean => {
  return !!(
    source.parsing_status &&
    ['queueing', 'uploading', 'parsing', 'captioning'].includes(source.parsing_status)
  );
};

/**
 * Check if a source has failed processing
 */
export const isSourceFailed = (source: Source): boolean => {
  return source.parsing_status === 'failed' || source.parsing_status === 'error';
};

/**
 * Check if RagFlow sync is in progress
 */
export const isRagflowSyncing = (source: Source): boolean => {
  return !!(
    source.ragflow_processing_status &&
    ['uploading', 'parsing'].includes(source.ragflow_processing_status)
  );
};

/**
 * Check if source is fully synced to RagFlow
 */
export const isRagflowSynced = (source: Source): boolean => {
  return source.ragflow_processing_status === 'completed';
};

/**
 * Get combined status text for source
 */
export const getSourceStatusText = (source: Source): string => {
  if (isSourceFailed(source)) {
    return 'Failed';
  }

  if (isSourceProcessing(source)) {
    return getProcessingStatusText(source.parsing_status);
  }

  if (isRagflowSyncing(source)) {
    return 'RAGFlowing to knowledge base...';
  }

  if (isRagflowSynced(source)) {
    return 'RAGFlow synced';
  }

  return 'Ready';
};
