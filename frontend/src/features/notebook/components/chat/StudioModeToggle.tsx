/**
 * Studio Mode Toggle Button
 *
 * A toggle button that appears in the chat input area (bottom-left),
 * similar to ChatGPT's search button. When activated, chat messages
 * are routed to the Coordinator instead of normal chat.
 */

import React from 'react';
import { Sparkles } from 'lucide-react';
import { cn } from '@/shared/utils/utils';
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from '@/shared/components/ui/tooltip';

interface StudioModeToggleProps {
    isActive: boolean;
    onToggle: () => void;
    disabled?: boolean;
    className?: string;
}

const StudioModeToggle: React.FC<StudioModeToggleProps> = ({
    isActive,
    onToggle,
    disabled = false,
    className,
}) => {
    return (
        <TooltipProvider>
            <Tooltip delayDuration={300}>
                <TooltipTrigger asChild>
                    <button
                        type="button"
                        onClick={onToggle}
                        disabled={disabled}
                        className={cn(
                            'h-8 w-8 rounded-lg flex items-center justify-center transition-all duration-200',
                            'focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-[#CE0E2D]/50',
                            isActive
                                ? 'bg-gradient-to-br from-[#CE0E2D] to-[#FF4D6A] text-white shadow-md'
                                : 'bg-[#F5F5F5] text-[#666666] hover:bg-[#E8E8E8] hover:text-[#1E1E1E]',
                            disabled && 'opacity-50 cursor-not-allowed',
                            className
                        )}
                        aria-label={isActive ? 'Disable Studio Mode' : 'Enable Studio Mode'}
                        aria-pressed={isActive}
                    >
                        <Sparkles
                            className={cn(
                                'h-4 w-4 transition-transform',
                                isActive && 'animate-pulse'
                            )}
                        />
                    </button>
                </TooltipTrigger>
                <TooltipContent side="top" className="text-xs">
                    {isActive ? (
                        <span>
                            <strong>Studio Mode Active</strong>
                            <br />
                            Click to switch to normal chat
                        </span>
                    ) : (
                        <span>
                            <strong>Enable Studio Mode</strong>
                            <br />
                            Use AI agents for research & reports
                        </span>
                    )}
                </TooltipContent>
            </Tooltip>
        </TooltipProvider>
    );
};

export default React.memo(StudioModeToggle);
