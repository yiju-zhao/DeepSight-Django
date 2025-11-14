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
    <header className="flex-shrink-0 relative z-10 border-b border-[#E3E3E3] bg-white/90 backdrop-blur">
      <div className="px-4 md:px-10 lg:px-20 py-3 flex justify-between items-center">
        <div className="flex items-center space-x-3">
          {/* Back Button */}
          {showBackButton && (
            <button
              onClick={() => navigate(backPath)}
              className="p-2 rounded-lg bg-white hover:bg-[#F7F7F7] border border-[#E3E3E3] transition-colors duration-200"
              title={`Back to ${backPath === "/deepdive" ? "DeepDive" : "Previous Page"}`}
            >
              <ArrowLeft className="h-5 w-5 text-[#1E1E1E]" />
            </button>
          )}

          {/* Title with simple styling */}
          {notebookTitle && (
            <div className="ml-2 flex flex-col">
              <span className="text-[11px] uppercase tracking-[0.3px] text-[#7B7B7B]">
                DeepDive Notebook
              </span>
              <h1 className="text-[20px] md:text-[24px] font-bold text-[#1E1E1E] leading-tight mt-0.5">
                {notebookTitle}
              </h1>
            </div>
          )}
        </div>

        {/* Logout Button */}
        <div className="flex items-center space-x-3">
          <button
            onClick={handleLogout}
            className="p-2 rounded-lg bg-white hover:bg-[#F7F7F7] border border-[#E3E3E3] text-[#1E1E1E] hover:text-black transition-colors duration-200"
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
