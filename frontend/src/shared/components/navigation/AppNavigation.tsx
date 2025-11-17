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
  LogOut,
  ChevronsLeft
} from 'lucide-react';
import { useAuth } from '@/shared/hooks/useAuth';

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
  const [expandedItems, setExpandedItems] = useState<string[]>([]);

  // Collapse state with localStorage persistence
  const [isExpanded, setIsExpanded] = useState(() => {
    const saved = localStorage.getItem('navigation-expanded');
    return saved ? JSON.parse(saved) : true;
  });

  const location = useLocation();
  const { handleLogout } = useAuth();

  // Persist expanded state to localStorage
  useEffect(() => {
    localStorage.setItem('navigation-expanded', JSON.stringify(isExpanded));
  }, [isExpanded]);

  // Calculate navigation width based on expanded state
  const navWidth = isExpanded ? 320 : 72;

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
    const isItemExpanded = expandedItems.includes(item.path);
    const paddingLeft = depth > 0 ? 'pl-8' : '';

    return (
      <div key={item.path} className="w-full">
        <div
          className={`flex items-center justify-between w-full rounded-lg transition-all duration-300 ease-out ${
            isExpanded ? 'space-x-3 px-4' : 'justify-center px-2'
          } py-3 ${paddingLeft} ${
            isActive
              ? 'opacity-100 font-bold bg-[#F5F5F5]'
              : 'opacity-60 hover:opacity-100 hover:bg-[#F5F5F5]'
          }`}
        >
          <Link
            to={item.path}
            className={`flex items-center ${isExpanded ? 'space-x-3' : ''} flex-1 ${!isExpanded ? 'justify-center' : ''}`}
            title={!isExpanded ? item.label : undefined}
          >
            <div className="text-[#1E1E1E]">{item.icon}</div>
            {isExpanded && <span className="font-medium text-sm text-[#1E1E1E]">{item.label}</span>}
          </Link>

          {hasChildren && isExpanded && (
            <button
              onClick={() => toggleExpanded(item.path)}
              className="p-1 rounded hover:bg-[#E3E3E3] transition-colors duration-300"
            >
              <ChevronDown
                className={`h-4 w-4 text-[#666666] transition-transform duration-300 ${
                  isItemExpanded ? 'rotate-180' : ''
                }`}
              />
            </button>
          )}
        </div>

        {hasChildren && isExpanded && (
          <AnimatePresence>
            {isItemExpanded && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3, ease: "easeOut" }}
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
    <motion.aside
      animate={{ width: navWidth }}
      transition={{ type: 'spring', damping: 30, stiffness: 300 }}
      className={`bg-white border border-[#E3E3E3] shadow-huawei-sm rounded-xl overflow-hidden ${className}`}
    >
      <div className={`${isExpanded ? 'p-6' : 'p-4'} flex flex-col h-full`}>
        {/* Header - Adaptive for collapsed state */}
        <div className="mb-8">
          {isExpanded ? (
            <div className="flex items-center space-x-3">
              <div className="w-2 h-12 bg-gradient-to-b from-blue-500 to-purple-600 rounded-full"></div>
              <div>
                <h1 className="text-2xl font-bold text-[#1E1E1E]">DeepSight</h1>
                <p className="text-sm text-[#666666]">AI Research Platform</p>
              </div>
            </div>
          ) : (
            <div className="flex justify-center">
              <div
                className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600
                            rounded-lg flex items-center justify-center shadow-huawei-sm"
              >
                <span className="text-white font-bold text-lg">D</span>
              </div>
            </div>
          )}
        </div>

        {/* Navigation Items */}
        <nav className="space-y-2 flex-1">
          {navigationItems.map(item => renderNavigationItem(item))}
        </nav>

        {/* Footer */}
        <div className="mt-auto pt-6 border-t border-[#E3E3E3]">
          {isExpanded && (
            <p className="text-xs text-[#666666] mb-4">
              © 2024 DeepSight. All rights reserved.
            </p>
          )}

          {/* Logout Button - Huawei Design Style */}
          <div className={`${isExpanded ? 'pt-4 border-t border-[#E3E3E3]' : ''}`}>
            <button
              onClick={handleLogout}
              className={`flex items-center w-full rounded-lg
                          ${isExpanded ? 'space-x-3 px-4' : 'justify-center px-2'}
                          py-3
                          text-[#1E1E1E] hover:bg-[#F5F5F5]
                          transition-colors duration-300 ease-out group`}
              title={!isExpanded ? 'Logout' : undefined}
            >
              <LogOut className="h-5 w-5 text-[#666666] group-hover:text-[#1E1E1E] transition-colors duration-300" />
              {isExpanded && <span className="font-medium text-sm">Logout</span>}
            </button>
          </div>

          {/* Expand/Collapse Toggle Button - Huawei Design */}
          <div className={`${isExpanded ? 'pt-4' : 'pt-2'}`}>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="w-full p-3 flex items-center justify-center
                         hover:bg-[#F5F5F5] rounded-lg
                         transition-colors duration-300 ease-out"
              aria-label={isExpanded ? 'Collapse Sidebar' : 'Expand Sidebar'}
              title={isExpanded ? 'Collapse Sidebar' : 'Expand Sidebar'}
            >
              <ChevronsLeft
                className={`h-5 w-5 text-[#666666] transition-transform duration-300 ease-out
                            ${!isExpanded ? 'rotate-180' : ''}`}
              />
            </button>
          </div>
        </div>
      </div>
    </motion.aside>
  );
};

export default AppNavigation;
