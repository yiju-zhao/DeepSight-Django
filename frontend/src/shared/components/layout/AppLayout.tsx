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
    <div className={`relative min-h-screen ${className}`}>
      {showNavigation && <AppNavigation />}
      <main className="w-full">
        {children}
      </main>
    </div>
  );
};

export default AppLayout;