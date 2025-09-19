import React from "react";
import { BarChart3, LogOut } from "lucide-react";
import { useAuth } from "@/shared/hooks/useAuth";

interface DashboardPageHeaderProps {
  title?: string;
  subtitle?: string;
}

/**
 * Header component for dashboard pages following DeepDive design pattern
 * Features gradient background, blur effect, and consistent styling
 */
const DashboardPageHeader: React.FC<DashboardPageHeaderProps> = ({
  title = "Dashboard",
  subtitle = "AI-powered insights and analytics"
}) => {
  const { handleLogout } = useAuth();

  return (
    <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200/60 sticky top-0 z-40">
      <div className="w-full px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          <div className="flex items-center space-x-4 ml-16">{/* Add left margin for navigation button */}
            <div className="flex items-center space-x-4">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center">
                <BarChart3 className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
                <p className="text-sm text-gray-500">{subtitle}</p>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleLogout}
              className="p-3 rounded-lg hover:bg-gray-100 transition-colors"
              title="Log out"
            >
              <LogOut className="w-6 h-6 text-gray-600" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default DashboardPageHeader;