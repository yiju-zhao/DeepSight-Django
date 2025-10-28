import React, { useCallback } from 'react';
import { Checkbox } from '@/shared/components/ui/checkbox';
import { ImageIcon } from 'lucide-react';
import { supportsPreview } from '@/features/notebook/utils/filePreview';
import { Source } from '@/features/notebook/type';

interface SourceItemProps {
  source: Source;
  onToggle: (id: string) => void;
  onPreview: (source: Source) => void;
  getSourceTooltip: (source: Source) => string;
  getPrincipleFileIcon: (source: Source) => React.ComponentType<any>;
  renderFileStatus: (source: Source) => React.ReactNode;
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
  renderFileStatus
}) => {
  // Unified working/ready state across parsing/ragflow/captioning
  const parsing = source.parsing_status;
  const rag = source.ragflow_processing_status;
  const caption = source.captioning_status;
  const isWorking = !!(
    (parsing && ['uploading', 'queueing', 'parsing'].includes(parsing)) ||
    (rag && ['uploading', 'parsing'].includes(rag)) ||
    caption === 'in_progress'
  );
  const isContentReady = !isWorking;
  const isCaptionReady = caption === 'completed';

  const handleItemClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Only allow preview when not working
    if (!isWorking && supportsPreview(source.metadata?.file_extension || source.ext || '', source.metadata || {})) {
      onPreview(source);
    }
  }, [onPreview, source, isWorking]);

  const supportsPreviewCheck = supportsPreview(
    source.metadata?.file_extension || source.ext || '',
    source.metadata || {}
  ) && !isWorking;

  return (
    <div
      className={`relative px-3 py-2.5 overflow-hidden rounded-lg bg-white transition-shadow ${
        supportsPreviewCheck ? 'cursor-pointer hover:shadow-sm' : ''
      } ${source.selected ? 'shadow-sm' : ''}`}
      onClick={supportsPreviewCheck ? handleItemClick : undefined}
      title={supportsPreviewCheck ? getSourceTooltip(source) : undefined}
    >
      {/* Sweeping highlight effect only during active processing */}
      {isWorking && (
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
            {React.createElement(getPrincipleFileIcon(source), {
              className: "h-4 w-4 text-gray-600"
            })}
          </div>
        </div>

        <div className="min-w-0 flex-1 flex items-center space-x-2">
          <h4 className="text-sm font-medium text-gray-900 truncate">{source.title}</h4>
          {renderFileStatus(source)}
        </div>

        <div className="flex items-center space-x-2 flex-shrink-0">
          {/* Show image icon when caption is ready */}
          {isCaptionReady && (
            <div title="Caption ready">
              <ImageIcon className="h-4 w-4 text-green-600" />
            </div>
          )}

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
