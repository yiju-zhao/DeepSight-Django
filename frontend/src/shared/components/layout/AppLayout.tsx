import React from 'react';
import AppNavigation from '../navigation/AppNavigation';

interface AppLayoutProps {
  children: React.ReactNode;
  showNavigation?: boolean;
  className?: string;
}

/**
 * Main application layout wrapper
 * Provides consistent structure and navigation across all pages
 */
const AppLayout: React.FC<AppLayoutProps> = ({
  children,
  showNavigation = true,
  className = ''
}) => {
  return (
    <div className={`min-h-screen bg-[#F5F5F5] ${className}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col lg:flex-row gap-6">
          {showNavigation && (
            <aside className="lg:w-80 lg:flex-shrink-0">
              <div className="sticky top-[100px]">
                <AppNavigation />
              </div>
            </aside>
          )}
          <main className="flex-1">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
};

export default AppLayout;
