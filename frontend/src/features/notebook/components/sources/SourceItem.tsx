import React, { useCallback } from 'react';
import { Checkbox } from '@/shared/components/ui/checkbox';
import { Loader2, AlertCircle } from 'lucide-react';
import { supportsPreview } from '@/features/notebook/utils/filePreview';
import { Source } from '@/features/notebook/type';

interface SourceItemProps {
  source: Source;
  onToggle: (id: string) => void;
  onPreview: (source: Source) => void;
  getSourceTooltip: (source: Source) => string;
  getPrincipleFileIcon: (source: Source) => React.ComponentType<any>;
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
  getPrincipleFileIcon
}) => {
  // Derive a minimal tri-state: processing | failed | done
  const deriveStatus = (s: Source): 'processing' | 'failed' | 'done' => {
    const p = s.parsing_status;
    const r = s.ragflow_processing_status;
    const c = s.captioning_status;
    // Failed has priority
    if (
      (p && ['failed', 'error', 'cancelled', 'unsupported'].includes(p)) ||
      r === 'failed' ||
      c === 'failed'
    ) {
      return 'failed';
    }
    // Processing: uploading/queueing/parsing/captioning/in_progress or explicit uploading placeholder
    if (
      (p && ['uploading', 'queueing', 'parsing', 'captioning'].includes(p)) ||
      (r && ['uploading', 'parsing'].includes(r)) ||
      c === 'in_progress' ||
      s.type === 'uploading'
    ) {
      return 'processing';
    }
    // Done: parsing has no 'completed', only 'done'; others may have 'completed'.
    // For UI, treat absence of failure/processing as done.
    return 'done';
  };

  const status = deriveStatus(source);
  const isProcessing = status === 'processing';
  const isFailed = status === 'failed';
  const isDone = status === 'done';
  const isSweeping = isProcessing; // sweep only when processing
  const isContentReady = isDone; // only final items are interactive/selectable

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
      className={`relative px-3 py-2.5 overflow-hidden rounded-lg bg-white transition-shadow ${
        supportsPreviewCheck ? 'cursor-pointer hover:shadow-sm' : ''
      } ${source.selected ? 'shadow-sm' : ''}`}
      onClick={supportsPreviewCheck ? handleItemClick : undefined}
      title={supportsPreviewCheck ? getSourceTooltip(source) : undefined}
    >
      {/* Sweeping highlight effect only during core parsing/uploading */}
      {isSweeping && (
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div
            className="absolute inset-0 bg-gradient-to-r from-transparent via-blue-100/40 to-transparent"
            style={{
              animation: 'sweepAnimation 2s ease-in-out infinite',
              transform: 'translateX(-100%)'
            }}
          />
        </div>
      )}

      <div className="flex items-center space-x-3 relative z-10">
        <div className="flex-shrink-0 flex items-center">
          <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center">
            {isProcessing ? (
              <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />
            ) : (
              React.createElement(getPrincipleFileIcon(source), {
                className: "h-4 w-4 text-gray-600"
              })
            )}
          </div>
        </div>

        <div className="min-w-0 flex-1 flex items-center space-x-2">
          <h4 className="text-sm font-medium text-gray-900 truncate">{source.title}</h4>
          {isFailed && (
            <div className="flex items-center space-x-1" title="Failed">
              <AlertCircle className="h-3 w-3 text-red-500" />
              <span className="text-xs text-red-500">Failed</span>
            </div>
          )}
        </div>

        <div className="flex items-center space-x-2 flex-shrink-0">
          {/* Only show checkbox when content is ready */}
          {isContentReady && (
            <div
              className="flex items-center cursor-pointer"
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
