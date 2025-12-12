// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Component focused solely on podcast generation configuration

import React, { useState } from 'react';
import {
  MessageSquare,
  Edit
} from 'lucide-react';
import { Button } from "@/shared/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/shared/components/ui/tooltip";
import { GenerationState } from './types';

// TypeScript interfaces
interface PodcastConfig {
  title?: string;
  description?: string;
  topic?: string;
  language?: 'en' | 'zh' | string;
}

interface FileItem {
  id: string;
  name: string;
  type: string;
  size?: number;
  url?: string;
}

interface PodcastGenerationFormProps {
  // Configuration props
  config: PodcastConfig;
  onConfigChange: (config: Partial<PodcastConfig>) => void;

  // Generation state props
  generationState: {
    state: GenerationState;
    progress?: string;
    error?: string;
  };
  onGenerate: (configOverrides?: Partial<PodcastConfig>) => void;

  // File selection props
  selectedFiles: FileItem[];
  selectedSources: any[];

  // Modal props
  onOpenModal: (modalType: string, data: React.ReactNode) => void;
  onCloseModal: (modalType: string) => void;
}

// ====== INTERFACE SEGREGATION PRINCIPLE (ISP) ======
// Focused props interface for podcast configuration
const PodcastGenerationForm: React.FC<PodcastGenerationFormProps> = ({
  // Configuration props
  config,
  onConfigChange,

  // Generation state props
  generationState,
  onGenerate,

  // File selection props
  selectedFiles,
  selectedSources,

  // Modal props
  onOpenModal,
  onCloseModal,

}) => {
  // ====== SINGLE RESPONSIBILITY: Validation logic ======
  const hasSelectedFiles = selectedFiles.length > 0;
  const canGenerate = hasSelectedFiles && generationState.state !== GenerationState.GENERATING;
  const isGenerating = generationState.state === GenerationState.GENERATING;

  const containerClasses = [
    'rounded-2xl relative overflow-hidden transition-all duration-200 min-h-[140px] flex flex-col justify-between',
    'bg-white border border-border shadow-[0_4px_8px_rgba(0,0,0,0.04)]',
    canGenerate && !isGenerating
      ? 'cursor-pointer hover:shadow-[0_12px_20px_rgba(0,0,0,0.12)] hover:border-accent-red group'
      : '',
    isGenerating ? 'ring-1 ring-accent-red' : ''
  ].join(' ');

  const tooltipContent = !hasSelectedFiles ? "Select files to generate a podcast" : "";

  return (
    <TooltipProvider>
      <Tooltip delayDuration={300}>
        <TooltipTrigger asChild>
          <div
            className={containerClasses}
            onClick={() => {
              if (canGenerate) {
                onGenerate();
              }
            }}
            aria-busy={isGenerating}
          >
            <div className="absolute top-4 left-4">
              <div className="w-8 h-8 bg-secondary rounded-full flex items-center justify-center group-hover:bg-red-50 transition-colors">
                <MessageSquare className="h-4 w-4 text-accent-red" />
              </div>
            </div>

            {/* Customize button in top right */}
            <div className="absolute top-4 right-4">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-muted-foreground hover:text-gray-900 hover:bg-secondary rounded-lg"
                onClick={(e) => {
                  e.stopPropagation();
                  // Import CustomizeModal component dynamically
                  import('./CustomizeModal').then(({ default: CustomizeModal }) => {
                    const customizeContent = (
                      <CustomizeModal
                        isOpen={true}
                        onClose={() => onCloseModal('customizePodcast')}
                        config={config}
                        onConfigChange={onConfigChange}
                        type="podcast"
                        selectedFiles={selectedFiles}
                        onGenerate={(configOverrides) => onGenerate(configOverrides)}
                      />
                    );
                    onOpenModal('customizePodcast', customizeContent);
                  });
                }}
              >
                <Edit className="h-4 w-4" />
              </Button>
            </div>

            <div className="p-5 pt-16">
              <h3 className="text-[14px] font-bold text-gray-900 mb-1">AI Podcast</h3>
              <p className="text-[12px] text-muted-foreground leading-[1.5]">Create an audio conversation from your notebook sources.</p>
            </div>
          </div>
        </TooltipTrigger>
        {tooltipContent && <TooltipContent>{tooltipContent}</TooltipContent>}
      </Tooltip>
    </TooltipProvider>
  );
};

export default React.memo(PodcastGenerationForm); // Performance optimization
