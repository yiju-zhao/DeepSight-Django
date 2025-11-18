import React from "react";
import { ArrowLeft, BookOpen } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface NotebookHeaderProps {
  notebookTitle?: string;
  showBackButton?: boolean;
  backPath?: string;
}

/**
 * Header component for notebook pages following Huawei Design Guide
 * Features:
 * - Clean typography following Huawei scale (28px → 24px → 20px)
 * - Minimalist design with generous white space
 * - Consistent colors: #1E1E1E (primary), #666666 (secondary)
 * - Icon integration matching MainPageHeader pattern
 */
const NotebookHeader: React.FC<NotebookHeaderProps> = ({
  notebookTitle,
  showBackButton = true,
  backPath = "/notebooks"
}) => {
  const navigate = useNavigate();

  return (
    <header className="bg-white shadow-sm">
      <div className="px-4 sm:px-6 lg:px-8 py-3">
        <div className="flex items-center space-x-3">
          {/* Back Button */}
          {showBackButton && (
            <button
              onClick={() => navigate(backPath)}
              className="p-2 rounded-lg bg-white hover:bg-[#F7F7F7] shadow-sm hover:shadow-md transition-all duration-300"
              title="Back to Notebooks"
            >
              <ArrowLeft className="h-5 w-5 text-[#1E1E1E]" />
            </button>
          )}

          <div className="flex items-center space-x-3">
            {/* Icon Container */}
            <div className="w-8 h-8 flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-[#CE0E2D]" />
            </div>

            {/* Title Section - Compact */}
            <h1 className="text-[16px] md:text-[18px] font-semibold text-[#1E1E1E] leading-tight">
              {notebookTitle || 'Untitled Notebook'}
            </h1>
          </div>
        </div>
      </div>
    </header>
  );
};

export default NotebookHeader;
