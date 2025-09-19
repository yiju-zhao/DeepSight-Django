/**
 * Dashboard action buttons component
 * Handles the floating action buttons on the right side
 */

import React from 'react';
import { LayoutGrid, List, Languages } from 'lucide-react';

interface DashboardActionsProps {
  onViewModeChange: () => void;
  onLanguageChange: () => void;
  viewMode?: 'list' | 'grid';
  language?: 'en' | 'zh';
  className?: string;
}

const DashboardActions: React.FC<DashboardActionsProps> = ({
  onViewModeChange,
  onLanguageChange,
  viewMode = 'list',
  language = 'en',
  className = '',
}) => {
  return (
    <div className={`fixed right-5 md:right-8 top-1/2 -translate-y-1/2 flex flex-col space-y-3 z-10 ${className}`}>
      {/* View Mode Toggle */}
      <button
        onClick={onViewModeChange}
        className="w-10 h-10 md:w-11 md:h-11 rounded-full bg-white/90 border border-gray-200 backdrop-blur-sm flex items-center justify-center text-gray-700 hover:bg-gray-50 shadow-sm transition"
        title={`Switch to ${viewMode === 'list' ? 'grid' : 'list'} view`}
        aria-label={`Switch to ${viewMode === 'list' ? 'grid' : 'list'} view`}
      >
        {viewMode === 'list' ? (
          <LayoutGrid className="h-5 w-5" />
        ) : (
          <List className="h-5 w-5" />
        )}
      </button>

      {/* Language Toggle */}
      <button
        onClick={onLanguageChange}
        className="w-10 h-10 md:w-11 md:h-11 rounded-full bg-white/90 border border-gray-200 backdrop-blur-sm flex items-center justify-center text-gray-700 hover:bg-gray-50 shadow-sm transition"
        title={`Switch to ${language === 'en' ? 'Chinese' : 'English'}`}
        aria-label={`Switch to ${language === 'en' ? 'Chinese' : 'English'}`}
      >
        <Languages className="h-5 w-5" />
      </button>
    </div>
  );
};

export default DashboardActions;
