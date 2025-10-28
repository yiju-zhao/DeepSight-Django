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
  // Simplified: only show failure; otherwise no inline status.
  const isFailed = source.parsing_status === 'failed' || source.parsing_status === 'error';
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
  return null;
};

/**
 * Renders RagFlow sync status indicator
 * Note: Completed status is shown via the larger icon in SourceItem.tsx
 */
// RagFlow sync indicators removed in simplified UX.

/**
 * Get human-readable text for processing status
 */
const getProcessingStatusText = (_status?: string): string => 'Processing...';

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
export const isRagflowSyncing = (_source: Source): boolean => false;

/**
 * Check if source is fully synced to RagFlow
 */
export const isRagflowSynced = (_source: Source): boolean => true;

/**
 * Get combined status text for source
 */
export const getSourceStatusText = (source: Source): string => (isSourceFailed(source) ? 'Failed' : 'Ready');
