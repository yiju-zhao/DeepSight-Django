import React from 'react';
import {
  Search,
  Settings,
} from 'lucide-react';
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
// Config-only card - generation happens via chat in Studio Mode
const ReportGenerationForm: React.FC<ReportGenerationFormProps> = ({
  config,
  onConfigChange,
  availableModels,
  generationState,
  onGenerate,
  selectedFiles,
  onOpenModal,
  onCloseModal,
}) => {
  const isGenerating = generationState.state === GenerationState.GENERATING;

  // Open configuration modal when card is clicked
  const handleCardClick = () => {
    if (isGenerating) return;

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
          // NOTE: onGenerate is no longer called from modal
          // Generation happens via natural language in Studio Mode
          onGenerate={() => {
            // Close modal - generation is via chat
            onCloseModal('customizeReport');
          }}
        />
      );
      onOpenModal('customizeReport', customizeContent);
    });
  };

  const containerClasses = [
    'rounded-2xl relative overflow-hidden transition-all duration-200 min-h-[140px] flex flex-col justify-between',
    'bg-white border border-[#E3E3E3] shadow-[0_4px_8px_rgba(0,0,0,0.04)]',
    !isGenerating
      ? 'cursor-pointer hover:shadow-[0_12px_20px_rgba(0,0,0,0.12)] hover:border-[#CE0E2D] group'
      : '',
    isGenerating ? 'ring-1 ring-[#CE0E2D] opacity-75' : ''
  ].join(' ');

  const tooltipContent = isGenerating
    ? "Report generation in progress"
    : "Click to configure report settings";

  return (
    <TooltipProvider>
      <Tooltip delayDuration={300}>
        <TooltipTrigger asChild>
          <div
            className={containerClasses}
            onClick={handleCardClick}
            aria-busy={isGenerating}
          >
            {/* Icon */}
            <div className="absolute top-4 left-4">
              <div className="w-8 h-8 bg-[#F5F5F5] rounded-full flex items-center justify-center group-hover:bg-[#FEF2F2] transition-colors">
                <Search className="h-4 w-4 text-[#CE0E2D]" />
              </div>
            </div>

            {/* Settings indicator */}
            <div className="absolute top-4 right-4">
              <div className="w-6 h-6 rounded-full flex items-center justify-center text-[#999999] group-hover:text-[#CE0E2D] transition-colors">
                <Settings className="h-3.5 w-3.5" />
              </div>
            </div>

            {/* Content */}
            <div className="p-5 pt-16">
              <h3 className="text-[14px] font-bold text-[#1E1E1E] mb-1">Research Report</h3>
              <p className="text-[12px] text-[#666666] leading-[1.5]">
                Configure settings for AI-powered research.
              </p>
              <p className="text-[10px] text-[#999999] mt-2 italic">
                Use Studio Mode in chat to generate
              </p>
            </div>
          </div>
        </TooltipTrigger>
        <TooltipContent>{tooltipContent}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

export default React.memo(ReportGenerationForm);

