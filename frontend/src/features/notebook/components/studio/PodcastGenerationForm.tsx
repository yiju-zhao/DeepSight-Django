// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Component focused solely on podcast generation configuration

import React, { useState } from 'react';
import {
  Play,
  Loader2,
  MessageSquare,
  Edit
} from 'lucide-react';
import { Button } from "@/shared/components/ui/button";
import { GenerationState } from './types';
import { COLORS } from "@/features/notebook/config/uiConfig";

// TypeScript interfaces
interface PodcastConfig {
  title?: string;
  description?: string;
  topic?: string;
  expert_names?: {
    host?: string;
    expert1?: string;
    expert2?: string;
  };
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

  return (
    <>
      <div className="bg-violet-50/40 rounded-2xl relative">
        {/* Customize button in top right */}
        <div className="absolute top-4 right-4">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0 text-violet-600 hover:text-violet-700 hover:bg-violet-100/50 rounded-lg"
            onClick={() => {
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

        {/* ====== SINGLE RESPONSIBILITY: Card content ====== */}
        <div className="p-5">
          {/* Card header with icon and info */}
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-10 h-10 bg-violet-100 rounded-full flex items-center justify-center">
              <MessageSquare className="h-5 w-5 text-violet-700" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Deep Dive Conversation</h3>
              <p className="text-sm text-gray-600">One host with two guests</p>
            </div>
          </div>

          {/* Action button */}
          <div className="relative group">
            <Button
              className={`w-full px-6 py-2 rounded-full transition-colors text-sm ${
                !canGenerate
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : `${COLORS.tw.primary.bg[600]} ${COLORS.tw.primary.hover.bg[700]} text-white`
              }`}
              onClick={() => onGenerate()}
              disabled={!canGenerate}
            >
              {generationState.state === GenerationState.GENERATING ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Generate
                </>
              )}
            </Button>
            {!canGenerate && (
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 whitespace-nowrap z-10">
                Select at least one source to generate
                <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-800"></div>
              </div>
            )}
          </div>
        </div>
      </div>

    </>
  );
};

export default React.memo(PodcastGenerationForm); // Performance optimization