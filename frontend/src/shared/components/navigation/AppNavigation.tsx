import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Home,
  BarChart3,
  Database,
  Brain,
  ChevronDown,
  TrendingUp,
  ArrowRight
} from 'lucide-react';

interface NavigationItem {
  path: string;
  label: string;
  icon: React.ReactNode;
  children?: NavigationItem[];
}

interface AppNavigationProps {
  className?: string;
}

const AppNavigation: React.FC<AppNavigationProps> = ({ className = '' }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isHoverZone, setIsHoverZone] = useState(false);
  const [expandedItems, setExpandedItems] = useState<string[]>([]);
  const [showHint, setShowHint] = useState(true);
  const location = useLocation();

  // Hide hint after 10 seconds or when navigation is used
  useEffect(() => {
    const timer = setTimeout(() => setShowHint(false), 10000);
    return () => clearTimeout(timer);
  }, []);

  // Auto-open on hover near left edge with intelligent closing
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const isNearLeftEdge = e.clientX <= 20;
      setIsHoverZone(isNearLeftEdge);

      if (isNearLeftEdge && !isOpen) {
        setIsOpen(true);
        setShowHint(false);
      } else if (isOpen && e.clientX > 320) {
        // Auto-close when mouse moves away from navigation area
        setIsOpen(false);
      }
    };

    document.addEventListener('mousemove', handleMouseMove);
    return () => document.removeEventListener('mousemove', handleMouseMove);
  }, [isOpen]);

  const navigationItems: NavigationItem[] = [
    {
      path: '/',
      label: 'Home',
      icon: <Home className="h-5 w-5" />
    },
    {
      path: '/dashboard',
      label: 'Dashboard',
      icon: <BarChart3 className="h-5 w-5" />,
      children: [
        {
          path: '/dashboard',
          label: 'Overview',
          icon: <BarChart3 className="h-4 w-4" />
        },
        {
          path: '/dashboard/conference',
          label: 'Conference Analysis',
          icon: <TrendingUp className="h-4 w-4" />
        }
      ]
    },
    {
      path: '/dataset',
      label: 'Dataset',
      icon: <Database className="h-5 w-5" />
    },
    {
      path: '/deepdive',
      label: 'DeepDive',
      icon: <Brain className="h-5 w-5" />
    }
  ];

  const toggleExpanded = (path: string) => {
    setExpandedItems(prev =>
      prev.includes(path)
        ? prev.filter(item => item !== path)
        : [...prev, path]
    );
  };

  const isActiveRoute = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  const renderNavigationItem = (item: NavigationItem, depth = 0) => {
    const isActive = isActiveRoute(item.path);
    const hasChildren = item.children && item.children.length > 0;
    const isExpanded = expandedItems.includes(item.path);
    const paddingLeft = depth > 0 ? 'pl-8' : 'pl-4';

    return (
      <div key={item.path} className="w-full">
        <div
          className={`flex items-center justify-between w-full py-3 px-4 rounded-lg transition-colors ${
            isActive
              ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-700'
              : 'text-gray-700 hover:bg-gray-50'
          } ${paddingLeft}`}
        >
          <Link
            to={item.path}
            className="flex items-center space-x-3 flex-1"
            onClick={() => !hasChildren && setIsOpen(false)}
          >
            {item.icon}
            <span className="font-medium">{item.label}</span>
          </Link>

          {hasChildren && (
            <button
              onClick={() => toggleExpanded(item.path)}
              className="p-1 rounded hover:bg-gray-200 transition-colors"
            >
              <ChevronDown
                className={`h-4 w-4 transition-transform ${
                  isExpanded ? 'rotate-180' : ''
                }`}
              />
            </button>
          )}
        </div>

        {hasChildren && (
          <AnimatePresence>
            {isExpanded && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="space-y-1 mt-1">
                  {item.children?.map(child => renderNavigationItem(child, depth + 1))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        )}
      </div>
    );
  };

  return (
    <>
      {/* Hover trigger zone - invisible area on left edge */}
      <div
        className="fixed left-0 top-0 w-5 h-full z-40"
        onMouseEnter={() => setIsHoverZone(true)}
      />

      {/* Navigation hint - shows initially to guide users */}
      <AnimatePresence>
        {showHint && (
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ delay: 2 }}
            className="fixed top-1/2 left-4 transform -translate-y-1/2 z-40 pointer-events-none"
          >
            <div className="bg-black/80 text-white px-3 py-2 rounded-lg shadow-lg flex items-center space-x-2 text-sm">
              <ArrowRight className="h-4 w-4" />
              <span>Hover left edge to navigate</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Hover zone indicator */}
      <motion.div
        className="fixed left-0 top-0 w-1 h-full bg-blue-500/30 z-30"
        initial={{ opacity: 0 }}
        animate={{ opacity: isHoverZone ? 1 : 0 }}
        transition={{ duration: 0.2 }}
      />

      {/* Navigation Sidebar */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop - covers entire screen including header */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black bg-opacity-20 z-[60]"
              onClick={() => setIsOpen(false)}
            />

            {/* Sidebar */}
            <motion.div
              initial={{ x: -320 }}
              animate={{ x: 0 }}
              exit={{ x: -320 }}
              transition={{ type: "spring", damping: 30, stiffness: 300 }}
              className="fixed left-0 top-0 h-full w-80 bg-white shadow-2xl z-[70] overflow-y-auto"
              onMouseEnter={() => {
                // Keep open when hovering sidebar
                setIsOpen(true);
              }}
            >
              <div className="p-6">
                {/* Header */}
                <div className="mb-8">
                  <div className="flex items-center space-x-3">
                    <div className="w-2 h-12 bg-gradient-to-b from-blue-500 to-purple-600 rounded-full"></div>
                    <div>
                      <h1 className="text-2xl font-bold text-gray-900">DeepSight</h1>
                      <p className="text-sm text-gray-600">AI Research Platform</p>
                    </div>
                  </div>
                </div>

                {/* Navigation Items */}
                <nav className="space-y-2">
                  {navigationItems.map(item => renderNavigationItem(item))}
                </nav>

                {/* Footer */}
                <div className="mt-12 pt-6 border-t border-gray-200">
                  <p className="text-xs text-gray-400">
                    © 2024 DeepSight. All rights reserved.
                  </p>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
};

export default AppNavigation;