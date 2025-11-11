import React, { useCallback } from 'react';
import { Checkbox } from '@/shared/components/ui/checkbox';
import { Loader2, AlertCircle, Image as ImageIcon, Trash2 } from 'lucide-react';
import { supportsPreview } from '@/features/notebook/utils/filePreview';
import { Source } from '@/features/notebook/type';

interface SourceItemProps {
  source: Source;
  onToggle: (id: string) => void;
  onPreview: (source: Source) => void;
  getSourceTooltip: (source: Source) => string;
  getPrincipleFileIcon: (source: Source) => React.ComponentType<any>;
  onDelete?: (source: Source) => void;
}

/**
 * Unified SourceItem component for consistent rendering across all source types
 * (PDF, URLs, media, documents, etc.)
 */
export const SourceItem = React.memo<SourceItemProps>(({ 
  source,
  onToggle,
  onPreview,
  getSourceTooltip,
  getPrincipleFileIcon,
  onDelete
}) => {
  // Derive a minimal tri-state: processing | failed | done
  // CRITICAL: Only show as 'done' when ragflow_processing_status === 'completed'
  const deriveStatus = (s: Source): 'processing' | 'failed' | 'done' => {
    const p = s.parsing_status;
    const r = s.ragflow_processing_status;
    const c = s.captioning_status;

    // Debug log: output current status values
    console.log(`[deriveStatus] Source ${s.id}:`, {
      parsing_status: p,
      ragflow_processing_status: r,
      captioning_status: c
    });

    // Failed has HIGHEST priority
    if (
      (p && ['failed', 'error', 'cancelled', 'unsupported'].includes(p)) ||
      r === 'failed' ||
      c === 'failed'
    ) {
      console.log(`[deriveStatus] → Returning 'failed' for source ${s.id}`);
      return 'failed';
    }

    // Processing: any state before RAGFlow completion
    // This includes: uploading, queueing, parsing, captioning, pending, etc.
    if (
      s.type === 'uploading' ||
      (p && ['uploading', 'queueing', 'parsing', 'captioning'].includes(p)) ||
      (r && ['pending', 'uploading', 'parsing'].includes(r)) ||
      c === 'in_progress' ||
      !r || // No RAGFlow status yet means still processing
      r === 'pending'
    ) {
      return 'processing';
    }

    // Done: ONLY when RAGFlow processing is completed
    if (r === 'completed') {
      return 'done';
    }

    // Default to processing for any unclear state
    return 'processing';
  };

  const status = deriveStatus(source);
  const isProcessing = status === 'processing';
  const isFailed = status === 'failed';
  const isDone = status === 'done';
  const isSweeping = isProcessing; // sweep only when processing
  const isContentReady = isDone; // only final items are interactive/selectable
  const isSelectable = isDone || isFailed; // allow selection for done or failed
  const showImageReady = source.captioning_status === 'completed';

  // Debug log: output selection status
  console.log(`[SourceItem] Source ${source.id}:`, {
    status,
    isFailed,
    isDone,
    isSelectable,
    selected: source.selected
  });

  const handleItemClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Only allow preview for final items
    if (isDone && supportsPreview(source.metadata?.file_extension || source.ext || '', source.metadata || {})) {
      onPreview(source);
    }
  }, [onPreview, source, isDone]);

  const supportsPreviewCheck = supportsPreview(
    source.metadata?.file_extension || source.ext || '',
    source.metadata || {}
  ) && isDone;

  return (
    <div
      className={`relative px-3 py-2.5 overflow-hidden transition-all duration-300 ${
        isProcessing
          ? 'bg-blue-50/50'
          : isFailed
          ? 'bg-red-50/50'
          : isDone && source.selected
          ? 'bg-red-50/40'
          : 'bg-white'
      } ${
        supportsPreviewCheck ? 'cursor-pointer hover:shadow-sm' : ''
      }`}
      onClick={supportsPreviewCheck ? handleItemClick : undefined}
      title={supportsPreviewCheck ? getSourceTooltip(source) : undefined}
    >
      {/* Sweeping highlight effect only during processing */}
      {isSweeping && (
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div
            className="absolute inset-0 bg-gradient-to-r from-transparent via-blue-200/50 to-transparent"
            style={{
              animation: 'sweepAnimation 2s ease-in-out infinite',
              transform: 'translateX(-100%)'
            }}
          />
        </div>
      )}

      <div className="flex items-center space-x-3 relative z-10">
        <div className="flex-shrink-0 flex items-center">
          <div className="w-8 h-8 flex items-center justify-center">
            {isProcessing ? (
              <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />
            ) : (
              React.createElement(getPrincipleFileIcon(source), {
                className: `h-4 w-4 transition-colors duration-300 ${
                  isDone ? 'text-gray-700' : 'text-gray-600'
                }`
              })
            )}
          </div>
        </div>

        <div className="min-w-0 flex-1 flex items-center space-x-2">
          <h4 className={`text-sm font-medium truncate transition-colors duration-300 ${
            isProcessing ? 'text-gray-600' : 'text-gray-900'
          }`}>
            {source.title}
          </h4>
          {isFailed && (
            <div className="flex items-center space-x-1" title="Failed">
              <AlertCircle className="h-3 w-3 text-red-500" />
              <span className="text-xs text-red-500">Failed</span>
            </div>
          )}
        </div>

        <div className="flex items-center space-x-2 flex-shrink-0">
          {/* Show image-ready indicator when captions are ready */}
          {showImageReady && (
            <div title="Image ready">
              <ImageIcon className="h-4 w-4 text-green-600" />
            </div>
          )}
          {isFailed && typeof onDelete === 'function' && (
            <button
              title="Delete failed source"
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); onDelete(source); }}
              className="text-red-600 hover:text-red-700"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}

          {/* Show checkbox when item is selectable (done or failed), but not during processing */}
          {isSelectable && (
            <div
              className="flex items-center cursor-pointer animate-in fade-in slide-in-from-right-2 duration-300"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
              }}
            >
              <Checkbox
                checked={source.selected}
                onCheckedChange={() => onToggle(String(source.id))}
                variant="default"
                size="default"
                className="cursor-pointer"
              />
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes sweepAnimation {
          0% {
            transform: translateX(-100%);
          }
          100% {
            transform: translateX(100%);
          }
        }
      `}</style>
    </div>
  );
});

SourceItem.displayName = 'SourceItem';
