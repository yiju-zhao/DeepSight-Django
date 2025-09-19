import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Home,
  BarChart3,
  Database,
  Brain,
  Menu,
  X,
  ChevronDown,
  TrendingUp
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
  const [expandedItems, setExpandedItems] = useState<string[]>([]);
  const location = useLocation();

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
                  {item.children.map(child => renderNavigationItem(child, depth + 1))}
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
      {/* Mobile/Desktop Navigation Toggle */}
      <div className={`fixed top-4 left-4 z-50 ${className}`}>
        <button
          onClick={() => setIsOpen(true)}
          className="p-3 bg-white rounded-lg shadow-lg border hover:bg-gray-50 transition-colors"
          aria-label="Open navigation"
        >
          <Menu className="h-6 w-6 text-gray-700" />
        </button>
      </div>

      {/* Navigation Sidebar */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black bg-opacity-50 z-40"
              onClick={() => setIsOpen(false)}
            />

            {/* Sidebar */}
            <motion.div
              initial={{ x: -320 }}
              animate={{ x: 0 }}
              exit={{ x: -320 }}
              transition={{ type: "spring", damping: 30, stiffness: 300 }}
              className="fixed left-0 top-0 h-full w-80 bg-white shadow-2xl z-50 overflow-y-auto"
            >
              <div className="p-6">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900">DeepSight</h1>
                    <p className="text-sm text-gray-600">AI Research Platform</p>
                  </div>
                  <button
                    onClick={() => setIsOpen(false)}
                    className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                    aria-label="Close navigation"
                  >
                    <X className="h-6 w-6 text-gray-700" />
                  </button>
                </div>

                {/* Navigation Items */}
                <nav className="space-y-2">
                  {navigationItems.map(item => renderNavigationItem(item))}
                </nav>

                {/* Footer */}
                <div className="mt-12 pt-6 border-t border-gray-200">
                  <p className="text-xs text-gray-500">
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