import React from 'react';
import { useRAGAgentState } from '@/features/notebook/hooks/useRAGAgentState';

const ChatAgentStatus: React.FC = () => {
    const { state, currentStepId, currentStepLabel, currentIndex, isCompleted } = useRAGAgentState();

    // Only render if we have a current step or active generation
    // And don't render if completely idle or finished (unless we want to show "Done" briefly)
    if (!state?.current_step && !state?.generation) return null;
    if (isCompleted || currentStepId === 'idle') return null;

    return (
        <div className="flex items-center justify-center py-2 bg-blue-50/50 border-b border-blue-100/50 transition-all duration-300">
            <div className="flex items-center space-x-2">
                <div className="relative flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
                </div>
                <span className="text-xs font-medium text-blue-700">
                    {currentStepLabel}
                </span>
            </div>
        </div>
    );
};

export default ChatAgentStatus;
