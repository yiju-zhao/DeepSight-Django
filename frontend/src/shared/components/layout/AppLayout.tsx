import React, { useState, useEffect } from 'react';
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
  // Sync with navigation expanded state from localStorage
  const [isNavExpanded, setIsNavExpanded] = useState(() => {
    const saved = localStorage.getItem('navigation-expanded');
    return saved ? JSON.parse(saved) : true;
  });

  // Listen to localStorage changes to sync navigation state
  useEffect(() => {
    const handleStorageChange = () => {
      const saved = localStorage.getItem('navigation-expanded');
      setIsNavExpanded(saved ? JSON.parse(saved) : true);
    };

    // Listen to storage events from other tabs/windows
    window.addEventListener('storage', handleStorageChange);

    // Custom event for same-tab updates
    const handleCustomEvent = (e: CustomEvent) => {
      setIsNavExpanded(e.detail);
    };
    window.addEventListener('navigation-state-change' as any, handleCustomEvent as any);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('navigation-state-change' as any, handleCustomEvent as any);
    };
  }, []);

  // Calculate margin based on navigation state (only on desktop)
  const mainMarginLeft = showNavigation
    ? (isNavExpanded ? 'lg:ml-[240px]' : 'lg:ml-[72px]')
    : 'ml-0';

  return (
    <div className={`min-h-screen bg-[#F5F5F5] ${className}`}>
      {/* Fixed Navigation - rendered outside main content flow */}
      {showNavigation && <AppNavigation />}

      {/* Main Content - offset by navigation width on desktop only */}
      <main
        className={`${mainMarginLeft} transition-all duration-300 ease-in-out min-h-screen bg-white`}
      >
        {children}
      </main>
    </div>
  );
};

export default AppLayout;
