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
    isGenerating
      ? 'bg-violet-100/70'
      : canGenerate
        ? 'bg-violet-100/50 cursor-pointer hover:bg-violet-100/70'
        : 'bg-violet-50/50' // Changed from opacity-60 and removed hover effect and cursor-not-allowed
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
            {/* Icon in top left */}
            <div className="absolute top-4 left-4">
              <div className="w-8 h-8 bg-violet-100 rounded-full flex items-center justify-center">
                <MessageSquare className="h-4 w-4 text-violet-700" />
              </div>
            </div>

            {/* Customize button in top right */}
            <div className="absolute top-4 right-4">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-violet-600 hover:text-violet-700 hover:bg-violet-100/50 rounded-lg"
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

            {/* Title and subtitle at bottom */}
            <div className="p-5 pt-16">
              <h3 className="text font-semibold text-violet-800">Conversation</h3>
              <p className="text-sm text-violet-700">One host with two guests</p>
            </div>
          </div>
        </TooltipTrigger>
        {tooltipContent && <TooltipContent>{tooltipContent}</TooltipContent>}
      </Tooltip>
    </TooltipProvider>
  );
};

export default React.memo(PodcastGenerationForm); // Performance optimization
