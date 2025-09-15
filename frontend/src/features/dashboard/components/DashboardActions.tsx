/**
 * Dashboard action buttons component
 * Handles the floating action buttons on the right side
 */

import React from 'react';

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
    <div className={`fixed right-8 top-1/2 transform -translate-y-1/2 flex flex-col space-y-4 z-10 ${className}`}>
      {/* Grid View Button */}
      <button
        onClick={onViewModeChange}
        className="w-12 h-12 bg-gray-200 rounded-lg flex items-center justify-center hover:bg-gray-300 transition-colors shadow-lg"
        title={`Switch to ${viewMode === 'list' ? 'grid' : 'list'} view`}
        aria-label={`Switch to ${viewMode === 'list' ? 'grid' : 'list'} view`}
      >
        {viewMode === 'list' ? (
          <div className="grid grid-cols-2 gap-1">
            <div className="w-2 h-2 bg-gray-600 rounded"></div>
            <div className="w-2 h-2 bg-gray-600 rounded"></div>
            <div className="w-2 h-2 bg-gray-600 rounded"></div>
            <div className="w-2 h-2 bg-gray-600 rounded"></div>
          </div>
        ) : (
          <div className="flex flex-col space-y-1">
            <div className="w-6 h-1 bg-gray-600 rounded"></div>
            <div className="w-6 h-1 bg-gray-600 rounded"></div>
            <div className="w-6 h-1 bg-gray-600 rounded"></div>
          </div>
        )}
      </button>

      {/* Language Toggle Button */}
      <button
        onClick={onLanguageChange}
        className="w-12 h-12 bg-pink-500 rounded-full flex items-center justify-center text-white font-medium hover:bg-pink-600 transition-colors shadow-lg"
        title={`Switch to ${language === 'en' ? 'Chinese' : 'English'}`}
        aria-label={`Switch to ${language === 'en' ? 'Chinese' : 'English'}`}
      >
        {language === 'en' ? '中A' : 'En中'}
      </button>
    </div>
  );
};

export default DashboardActions;