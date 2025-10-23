// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Component focused solely on report generation configuration

import React, { useState } from 'react';
import {
  Search,
  Edit
} from 'lucide-react';
import { Button } from "@/shared/components/ui/button";
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

  return (
    <>
      <div
        className={`rounded-2xl relative transition-all duration-200 min-h-[140px] flex flex-col justify-between ${
          canGenerate
            ? 'bg-emerald-100/50 cursor-pointer hover:bg-emerald-100/70'
            : 'bg-emerald-50/30 cursor-not-allowed opacity-60'
        }`}
        onClick={() => {
          if (canGenerate) {
            onGenerate();
          }
        }}
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
          <h3 className="text-lg font-semibold text-gray-900">Report</h3>
          <p className="text-sm text-gray-600">Comprehensive AI-powered analysis</p>
        </div>

        {/* Tooltip removed for simplified UI */}
      </div>

    </>
  );
};

export default React.memo(ReportGenerationForm); // Performance optimization
