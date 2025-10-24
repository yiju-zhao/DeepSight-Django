import React from "react";
import { ArrowLeft, LogOut } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/shared/hooks/useAuth";

interface NotebookHeaderProps {
  notebookTitle?: string;
  showBackButton?: boolean;
  backPath?: string;
}

/**
 * Header component for notebook pages
 * Handles navigation, menu, and logout functionality
 */
const NotebookHeader: React.FC<NotebookHeaderProps> = ({
  notebookTitle,
  showBackButton = true,
  backPath = "/deepdive"
}) => {
  const navigate = useNavigate();
  const { handleLogout } = useAuth();

  return (
    <header className="flex-shrink-0 relative z-10">
      <div className="px-3 pt-2 pb-2 md:px-4 lg:px-5 flex justify-between items-center">
        <div className="flex items-center space-x-3">
          {/* Back Button */}
          {showBackButton && (
            <button
              onClick={() => navigate(backPath)}
              className="p-2 rounded-lg bg-white hover:bg-gray-50 border border-gray-200 transition-colors duration-200"
              title={`Back to ${backPath === "/deepdive" ? "DeepDive" : "Previous Page"}`}
            >
              <ArrowLeft className="h-5 w-5 text-gray-700" />
            </button>
          )}

          {/* Title with simple styling */}
          {notebookTitle && (
            <div className="ml-2 flex items-center space-x-2">
              <div className="w-0.5 h-6 bg-red-600 rounded-full"></div>
              <h1 className="text-xl font-semibold text-gray-900">
                {notebookTitle}
              </h1>
            </div>
          )}
        </div>

        {/* Logout Button */}
        <div className="flex items-center space-x-3">
          <button
            onClick={handleLogout}
            className="p-2 rounded-lg bg-white hover:bg-gray-50 border border-gray-200 text-gray-700 hover:text-gray-900 transition-colors duration-200"
            title="Logout"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      </div>
    </header>
  );
};

export default NotebookHeader;