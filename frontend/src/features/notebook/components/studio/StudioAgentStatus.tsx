import React, { useEffect, useRef } from 'react';
import { useRAGAgentState, STEPS_ORDER } from '@/features/notebook/hooks/useRAGAgentState';

const StudioAgentStatus: React.FC = () => {
    const { state, currentIndex, percentage, isCompleted } = useRAGAgentState();
    const scrollContainerRef = useRef<HTMLDivElement>(null);
    const activeStepRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to active step
    useEffect(() => {
        if (activeStepRef.current && scrollContainerRef.current) {
            activeStepRef.current.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
        }
    }, [currentIndex, isCompleted]);

    // Only render if we have a current step or active generation
    if (!state?.current_step && !state?.generation) {
        // Optional: Show empty state or nothing?
        // If nothing is happening, maybe show nothing in the progress area
        return (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 text-sm">
                <div className="mb-2">Ready to assist</div>
                <div className="text-xs">Ask a question to start the agent</div>
            </div>
        );
    }

    return (
        <div className="w-full h-full flex flex-col bg-white">
            {/* Header / Progress Bar Area */}
            <div 
                className="flex-none px-4 py-3 bg-white border-b border-gray-100 sticky top-0 z-10"
                data-testid="task-progress-header"
            >
                <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                        <span className={`h-2 w-2 rounded-full ${state?.generation || isCompleted ? 'bg-green-500' : 'bg-blue-500 animate-pulse'}`}></span>
                        <span className="text-sm font-semibold text-gray-700">
                            {isCompleted ? 'Completed' : (state?.current_step ? 'Agent Working...' : 'Ready')}
                        </span>
                    </div>
                    <span className="text-xs font-mono text-gray-500 font-medium">
                        {Math.round(percentage)}%
                    </span>
                </div>

                {/* Progress Bar */}
                <div className="relative h-1.5 rounded-full overflow-hidden bg-gray-100 w-full">
                    <div
                        className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all duration-1000 ease-out"
                        style={{ width: `${percentage}%` }}
                    />
                </div>
            </div>

                        {/* Steps Scroll Area */}
                        <div 
                            data-testid="task-progress"
                            className="flex-1 overflow-y-auto p-4 space-y-2"
                            ref={scrollContainerRef}
                        >
                            {STEPS_ORDER.map((step, index) => {
                                const isStepCompleted = index < currentIndex || isCompleted;
                                const isCurrentPending = index === currentIndex && !isCompleted;
            
                                return (
                                    <div
                                        key={step.id}
                                        ref={isCurrentPending ? activeStepRef : null}
                                        className={`relative flex items-center p-2 rounded-lg transition-all duration-500 ${isStepCompleted                                    ? "bg-green-50/50 border border-green-100"
                                    : isCurrentPending
                                        ? "bg-blue-50/50 border border-blue-100 shadow-sm"
                                        : "bg-gray-50/30 border border-gray-100"
                                    }`}
                            >
                                {/* Connector Line */}
                                {index < STEPS_ORDER.length - 1 && (
                                    <div className="absolute left-4 top-full w-0.5 h-2 bg-gray-200" style={{ height: '0.5rem', zIndex: 0 }} />
                                )}

                                {/* Status Icon */}
                                <div
                                    className={`relative z-10 flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center mr-3 ${isStepCompleted
                                        ? "bg-green-500 text-white shadow-sm"
                                        : isCurrentPending
                                            ? "bg-blue-500 text-white shadow-sm"
                                            : "bg-gray-200 text-gray-400"
                                        }`}
                                >
                                    {isStepCompleted ? (
                                        <CheckIcon />
                                    ) : isCurrentPending ? (
                                        <SpinnerIcon />
                                    ) : (
                                        <div className="w-1.5 h-1.5 bg-current rounded-full" />
                                    )}
                                </div>

                                {/* Step Content */}
                                <div className="flex-1 min-w-0">
                                    <div
                                        className={`font-medium transition-all duration-300 text-xs ${isStepCompleted
                                            ? "text-green-700"
                                            : isCurrentPending
                                                ? "text-blue-700 text-sm"
                                                : "text-gray-400"
                                            }`}
                                    >
                                        {step.label}
                                    </div>
                                    
                                    {isCurrentPending && (
                                        <div className="text-xs mt-0.5 animate-pulse text-blue-500/80">
                                            Processing...
                                        </div>
                                    )}

                                    {/* Sub-content for Reordering */}
                                    {step.id === 'reordering' && isStepCompleted && state?.semantic_groups && (
                                        <div className="mt-1 flex flex-wrap gap-1">
                                            {state.semantic_groups.map((g, i) => (
                                                <span key={i} className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-50 text-purple-700 border border-purple-100">
                                                    {g.group_name}
                                                </span>
                                            ))}
                                        </div>
                                    )}

                                    {/* Sub-content for Planning */}
                                    {step.id === 'planning' && isStepCompleted && state?.queries && (
                                        <div className="mt-1 text-[10px] text-gray-400 italic truncate">
                                            Planned {state.queries.length} searches
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}
            </div>
        </div>
    );
};

function CheckIcon() {
    return (
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
        </svg>
    );
}

function SpinnerIcon() {
    return (
        <svg
            className="w-3 h-3 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
        >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
        </svg>
    );
}

export default StudioAgentStatus;
