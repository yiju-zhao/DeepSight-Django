import React from "react";
import { LogOut, ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/shared/hooks/useAuth";

interface MainPageHeaderProps {
  title: string;
  subtitle?: string;
  icon: React.ReactNode;
  iconColor: string; // Tailwind color classes like "from-blue-500 to-blue-600"
  showBackButton?: boolean;
  backPath?: string;
  rightActions?: React.ReactNode; // For custom actions like language switcher
}

/**
 * Shared main header component following DeepDive design pattern
 * Features gradient background, blur effect, and consistent styling
 * Used across Dashboard, Dataset, and DeepDive pages with different colors and icons
 */
const MainPageHeader: React.FC<MainPageHeaderProps> = ({
  title,
  subtitle,
  icon,
  iconColor,
  showBackButton = false,
  backPath,
  rightActions
}) => {
  const navigate = useNavigate();
  const { handleLogout } = useAuth();

  return (
    <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200/60 sticky top-0 z-40">
      <div className="w-full px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          <div className="flex items-center space-x-4">{/* Removed large left margin */}
            {/* Back Button (for individual pages like notebook detail) */}
            {showBackButton && backPath && (
              <button
                onClick={() => navigate(backPath)}
                className="p-2.5 rounded-xl bg-gray-100/80 hover:bg-gray-200/80 transition-all duration-200 hover:scale-105 mr-2"
                title={`Back to ${backPath === "/deepdive" ? "DeepDive" : "Previous Page"}`}
              >
                <ArrowLeft className="h-5 w-5 text-gray-700" />
              </button>
            )}

            <div className="flex items-center space-x-4">
              {/* Icon with dynamic color */}
              <div className={`w-10 h-10 bg-gradient-to-br ${iconColor} rounded-xl flex items-center justify-center`}>
                {icon}
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
                {subtitle && <p className="text-sm text-gray-500">{subtitle}</p>}
              </div>
            </div>
          </div>

          {/* Right side actions */}
          <div className="flex items-center space-x-3">
            {/* Custom right actions (like language switcher) */}
            {rightActions}

            {/* Logout Button */}
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

export default MainPageHeader;