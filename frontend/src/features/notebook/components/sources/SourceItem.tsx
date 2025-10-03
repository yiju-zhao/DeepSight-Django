import React, { useCallback } from 'react';
import { Checkbox } from '@/shared/components/ui/checkbox';
import { CheckCircle2, ImageIcon } from 'lucide-react';
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
  // Determine status
  const isContentReady = source.parsing_status === 'done' || source.parsing_status === 'captioning';
  const isCaptionReady = source.captioning_status === 'done';
  const isRagflowReady = source.ragflow_processing_status === 'done';

  const handleItemClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (supportsPreview(source.metadata?.file_extension || source.ext || '', source.metadata || {})) {
      onPreview(source);
    }
  }, [onPreview, source]);

  const supportsPreviewCheck = supportsPreview(
    source.metadata?.file_extension || source.ext || '',
    source.metadata || {}
  );

  return (
    <div
      className={`relative px-3 py-2 border-b border-gray-100 overflow-hidden ${
        supportsPreviewCheck ? 'cursor-pointer hover:bg-gray-50' : ''
      } ${source.selected ? 'bg-red-50 border-red-200' : ''}`}
      onClick={supportsPreviewCheck ? handleItemClick : undefined}
      title={supportsPreviewCheck ? getSourceTooltip(source) : undefined}
    >
      <div className="flex items-center space-x-3">
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
            <ImageIcon className="h-4 w-4 text-green-600" title="Caption ready" />
          )}

          {/* Show checkmark when RagFlow upload is complete */}
          {isRagflowReady && (
            <CheckCircle2 className="h-4 w-4 text-green-600" title="RagFlow sync complete" />
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
    </div>
  );
});

SourceItem.displayName = 'SourceItem';
