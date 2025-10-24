import React, { useState } from 'react';
import {
  Search,
  Edit
} from 'lucide-react';
import { Button } from "@/shared/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/shared/components/ui/tooltip";
import { GenerationState } from "./types";

// Type definitions
interface ReportConfig {
  topic?: string;
  article_title?: string;
  model_provider?: string;
  retriever?: string;
  prompt_type?: string;
  include_image?: boolean;
  include_domains?: boolean;
  time_range?: string;
}

interface AvailableModels {
  model_providers?: string[];
}

interface FileItem {
  id: string;
  name: string;
  [key: string]: any;
}

interface ReportGenerationFormProps {
  config: ReportConfig;
  onConfigChange: (config: Partial<ReportConfig>) => void;
  availableModels: AvailableModels;
  generationState: {
    state: GenerationState;
    progress?: string;
    error?: string;
    isGenerating: boolean;
  };
  onGenerate: (configOverrides?: Partial<ReportConfig>) => void;
  selectedFiles: FileItem[];
  onOpenModal: (id: string, content: React.ReactNode) => void;
  onCloseModal: (id: string) => void;
}

// ====== INTERFACE SEGREGATION PRINCIPLE (ISP) ======
// Focused props interface for report configuration
const ReportGenerationForm: React.FC<ReportGenerationFormProps> = ({
  // Configuration props
  config,
  onConfigChange,
  availableModels,
  
  // Generation state props
  generationState,
  onGenerate,

  // File selection props
  selectedFiles,
  
  // Modal props
  onOpenModal,
  onCloseModal,

}) => {
  // ====== SINGLE RESPONSIBILITY: Validation logic ======
  const hasSelectedFiles = selectedFiles.length > 0;

  // ====== SINGLE RESPONSIBILITY: Model name formatting ======
  const formatModelName = (value: string): string => {
    return value.charAt(0).toUpperCase() + value.slice(1);
  };

  const canGenerate = hasSelectedFiles && generationState.state !== GenerationState.GENERATING;
  const isGenerating = generationState.state === GenerationState.GENERATING;

  const containerClasses = [
    'rounded-2xl relative overflow-hidden transition-all duration-200 min-h-[140px] flex flex-col justify-between',
    isGenerating
      ? 'bg-emerald-100/70 ring-1 ring-emerald-300'
      : canGenerate
        ? 'bg-emerald-100/50 cursor-pointer hover:bg-emerald-100/70'
        : 'bg-emerald-50/50' // Changed from opacity-60 and removed hover effect and cursor-not-allowed
  ].join(' ');

  const tooltipContent = !hasSelectedFiles ? "Select files to generate a report" : "";

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
              <div className="w-8 h-8 bg-emerald-100 rounded-full flex items-center justify-center">
                <Search className="h-4 w-4 text-emerald-700" />
              </div>
            </div>

            {/* Customize button in top right */}
            <div className="absolute top-4 right-4">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-100/50 rounded-lg"
                onClick={(e) => {
                  e.stopPropagation();
                  // Import CustomizeModal component dynamically
                  import('./CustomizeModal').then(({ default: CustomizeModal }) => {
                    const customizeContent = (
                      <CustomizeModal
                        isOpen={true}
                        onClose={() => onCloseModal('customizeReport')}
                        config={config}
                        onConfigChange={onConfigChange}
                        type="report"
                        selectedFiles={selectedFiles}
                        onGenerate={(configOverrides) => onGenerate(configOverrides)}
                      />
                    );
                    onOpenModal('customizeReport', customizeContent);
                  });
                }}
              >
                <Edit className="h-4 w-4" />
              </Button>
            </div>

            {/* Title and subtitle at bottom */}
            <div className="p-5 pt-16">
              <h3 className="text font-semibold text-emerald-800">Report</h3>
              <p className="text-sm text-emerald-700">AI-powered analysis</p>
            </div>
          </div>
        </TooltipTrigger>
        {tooltipContent && <TooltipContent>{tooltipContent}</TooltipContent>}
      </Tooltip>
    </TooltipProvider>
  );
};

export default React.memo(ReportGenerationForm); // Performance optimization
