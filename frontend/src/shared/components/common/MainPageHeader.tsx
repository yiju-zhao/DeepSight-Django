import React from "react";
import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface MainPageHeaderProps {
  title: string;
  subtitle?: string;
  label?: string; // Uppercase label like "DEEPSIGHT" or "RESEARCH"
  icon: React.ReactNode;
  iconColor?: string; // Icon color (not used if icon already has color)
  iconBgColor?: string; // Optional background color for icon
  showBackButton?: boolean;
  backPath?: string;
  rightActions?: React.ReactNode; // For custom actions like language switcher
  className?: string;
}

/**
 * Shared main header component following Huawei Design Guide
 * Features:
 * - Clean typography following Huawei scale (28px → 24px → 20px)
 * - Minimalist design with generous white space
 * - Consistent colors: #1E1E1E (primary), #666666 (secondary)
 * - Optional uppercase label with tracking
 * - Responsive design with proper breakpoints
 *
 * Used across Dashboard, Dataset, Conference, and Notebook pages
 */
const MainPageHeader: React.FC<MainPageHeaderProps> = ({
  title,
  subtitle,
  label,
  icon,
  iconColor,
  iconBgColor,
  showBackButton = false,
  backPath,
  rightActions,
  className = ''
}) => {
  const navigate = useNavigate();

  return (
    <header className={`bg-white ${className}`}>
      <div className="w-full px-4 sm:px-6 lg:px-8 py-6 md:py-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            {/* Back Button */}
            {showBackButton && backPath && (
              <button
                onClick={() => navigate(backPath)}
                className="p-2 rounded-lg bg-white hover:bg-[#F7F7F7] border border-[#E3E3E3] transition-colors duration-300"
                title="Go back"
              >
                <ArrowLeft className="h-5 w-5 text-[#1E1E1E]" />
              </button>
            )}

            <div className="flex items-center space-x-4">
              {/* Icon Container - Simple, no gradients */}
              <div
                className="w-10 h-10 flex items-center justify-center"
                style={iconBgColor ? { backgroundColor: iconBgColor, borderRadius: '8px' } : undefined}
              >
                {icon}
              </div>

              {/* Title Section */}
              <div>
                {label && (
                  <p className="text-[11px] uppercase tracking-[0.3px] text-[#7B7B7B] mb-0.5">
                    {label}
                  </p>
                )}
                <h1 className="text-[20px] md:text-[24px] lg:text-[28px] font-bold text-[#1E1E1E] leading-[1.321]">
                  {title}
                </h1>
                {subtitle && (
                  <p className="text-sm text-[#666666] mt-2 leading-relaxed">
                    {subtitle}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Right side actions */}
          {rightActions && (
            <div className="flex items-center space-x-3">
              {rightActions}
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default MainPageHeader;
