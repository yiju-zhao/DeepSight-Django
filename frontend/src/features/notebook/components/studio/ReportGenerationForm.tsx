// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Component focused solely on report generation configuration

import React, { useState } from 'react';
import {
  Search,
  FileText,
  Loader2,
  Edit
} from 'lucide-react';
import { Button } from "@/shared/components/ui/button";
import { GenerationState } from "./types";
import { COLORS } from "@/features/notebook/config/uiConfig";

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
      <div className="bg-emerald-50/40 rounded-2xl relative">
        {/* Customize button in top right */}
        <div className="absolute top-4 right-4">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-100/50 rounded-lg"
            onClick={() => {
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

        {/* ====== SINGLE RESPONSIBILITY: Card content ====== */}
        <div className="p-5">
          {/* Card header with icon and info */}
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-10 h-10 bg-emerald-100 rounded-full flex items-center justify-center">
              <Search className="h-5 w-5 text-emerald-700" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Research Report</h3>
              <p className="text-sm text-gray-600">Comprehensive AI-powered analysis</p>
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
                  <FileText className="mr-2 h-4 w-4" />
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

export default React.memo(ReportGenerationForm); // Performance optimization