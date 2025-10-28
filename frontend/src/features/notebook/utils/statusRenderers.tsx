import React from 'react';
import { Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Source } from '@/features/notebook/type';

/**
 * Status rendering utilities for knowledge base items
 * Handles parsing status, RagFlow sync status, and captioning status
 */

export interface StatusIndicatorProps { source: Source }

/**
 * Renders the file processing status indicator
 * Shows different states: queueing, parsing, uploading, captioning, syncing, completed, failed
 */
export const renderFileStatus = (source: Source): React.ReactNode => {
  const parsing = source.parsing_status;
  const rag = source.ragflow_processing_status;
  const caption = source.captioning_status;

  const isFailed = (parsing === 'failed' || parsing === 'error') || rag === 'failed' || caption === 'failed';
  if (isFailed) {
    return (
      <div className="flex items-center space-x-1">
        <AlertCircle className="h-3 w-3 text-red-500" />
        <span className="text-xs text-red-500">Failed</span>
      </div>
    );
  }

  const isWorking = !!(
    (parsing && ['uploading', 'queueing', 'parsing'].includes(parsing)) ||
    (rag && ['uploading', 'parsing'].includes(rag)) ||
    caption === 'in_progress' ||
    parsing === 'captioning'
  );
  if (isWorking) {
    let label = 'Processing';
    if (parsing === 'uploading' || rag === 'uploading') label = 'Uploading';
    else if (parsing === 'queueing') label = 'Queued';
    else if (parsing === 'parsing' || rag === 'parsing') label = 'Processing';
    else if (parsing === 'captioning' || caption === 'in_progress') label = 'Captioning';
    return (
      <div className="flex items-center space-x-1 text-blue-600">
        <Loader2 className="h-3 w-3 animate-spin" />
        <span className="text-xs">{label}</span>
      </div>
    );
  }

  const isCompleted = parsing === 'done' || rag === 'completed' || caption === 'completed';
  if (isCompleted) {
    return (
      <div className="flex items-center space-x-1 text-green-600" title="Ready">
        <CheckCircle2 className="h-3 w-3" />
        <span className="text-xs">Completed</span>
      </div>
    );
  }

  return null;
};

// Removed unused helpers to keep the renderer lean
