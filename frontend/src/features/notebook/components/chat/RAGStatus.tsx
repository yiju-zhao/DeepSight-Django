import React from 'react';
import { useCoAgentStateRender } from "@copilotkit/react-core";

// Define the state interface based on backend RAGAgentState
interface RAGAgentState {
    current_step?: string;
    semantic_groups?: {
        group_name: string;
        description: string;
        chunk_ids: number[];
    }[];
    queries?: string[];
    generation?: string;
}

// Map internal steps to display steps
const STEPS_ORDER = [
    { id: 'analyzing', label: 'Analyzing Request' },
    { id: 'planning', label: 'Planning Search Strategy' },
    { id: 'retrieving', label: 'Retrieving Documents' },
    { id: 'reordering', label: 'Organizing Information' },
    { id: 'synthesizing', label: 'Generating Answer' }
];

const RAGStatus: React.FC = () => {
    useCoAgentStateRender<RAGAgentState>({
        name: "rag_agent",
        render: ({ state }) => {
            // Only render if we have a current step or active generation
            if (!state.current_step && !state.generation) return null;

            const currentStepId = state.current_step || 'idle';

            // Calculate progress
            // If generation is complete (we have text and step is likely done or synthesizing), show full completion
            // Otherwise find index
            let currentIndex = STEPS_ORDER.findIndex(s => s.id === currentStepId);

            // Fallback for sub-steps like 'grade_relevance' mapping to 'retrieving' or similar if needed
            if (currentIndex === -1) {
                if (currentStepId === 'grade_relevance') currentIndex = 2; // Retrieving phase
                else if (currentStepId === 'prepare_generation') currentIndex = 4; // Synthesizing phase
                // idle check
                else if (state.generation) currentIndex = STEPS_ORDER.length; // Complete
                else currentIndex = 0;
            }

            // If we have a generation and we are at the end, mark all complete
            if (state.generation && (currentStepId === 'Synthesizing' || currentStepId === 'idle')) {
                currentIndex = STEPS_ORDER.length;
            }

            const progressPercentage = Math.min(((currentIndex) / STEPS_ORDER.length) * 100, 100);

            // Hardcode "light" theme for now or use context if available (assuming light for simplicity as per user setup)
            const theme = "light";

            return (
                <div className="flex justify-center my-4 w-full">
                    <div
                        data-testid="task-progress"
                        className={`relative rounded-xl w-full max-w-2xl p-6 shadow-lg backdrop-blur-sm bg-gradient-to-br from-white via-gray-50 to-white text-gray-800 border border-gray-200/80 mx-4`}
                    >
                        {/* Header */}
                        <div className="mb-5">
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="text-lg font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                                    DeepSight Agent
                                </h3>
                                <div className="text-sm text-gray-500">
                                    {Math.round(progressPercentage)}% Complete
                                </div>
                            </div>

                            {/* Progress Bar */}
                            <div className="relative h-2 rounded-full overflow-hidden bg-gray-200">
                                <div
                                    className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all duration-1000 ease-out"
                                    style={{ width: `${progressPercentage}%` }}
                                />
                                <div className="absolute top-0 left-0 h-full w-full bg-gradient-to-r from-transparent to-transparent animate-pulse via-white/40" />
                            </div>
                        </div>

                        {/* Steps */}
                        <div className="space-y-2">
                            {STEPS_ORDER.map((step, index) => {
                                const isCompleted = index < currentIndex;
                                const isCurrentPending = index === currentIndex;

                                return (
                                    <div
                                        key={step.id}
                                        className={`relative flex items-center p-2.5 rounded-lg transition-all duration-500 ${isCompleted
                                            ? "bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200/60"
                                            : isCurrentPending
                                                ? "bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200/60 shadow-md shadow-blue-200/50"
                                                : "bg-gray-50/50 border border-gray-200/60"
                                            }`}
                                    >
                                        {/* Connector Line */}
                                        {index < STEPS_ORDER.length - 1 && (
                                            <div className="absolute left-5 top-full w-0.5 h-2 bg-gradient-to-b from-gray-300 to-gray-400" />
                                        )}

                                        {/* Status Icon */}
                                        <div
                                            className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center mr-2 ${isCompleted
                                                ? "bg-gradient-to-br from-green-500 to-emerald-600 shadow-md shadow-green-200"
                                                : isCurrentPending
                                                    ? "bg-gradient-to-br from-blue-500 to-purple-600 shadow-md shadow-blue-200"
                                                    : "bg-gray-300 border border-gray-400"
                                                }`}
                                        >
                                            {isCompleted ? (
                                                <CheckIcon />
                                            ) : isCurrentPending ? (
                                                <SpinnerIcon />
                                            ) : (
                                                <ClockIcon />
                                            )}
                                        </div>

                                        {/* Step Content */}
                                        <div className="flex-1 min-w-0">
                                            <div
                                                className={`font-semibold transition-all duration-300 text-sm ${isCompleted
                                                    ? "text-green-700"
                                                    : isCurrentPending
                                                        ? "text-blue-700 text-base"
                                                        : "text-gray-500"
                                                    }`}
                                            >
                                                {step.label}
                                            </div>
                                            {isCurrentPending && (
                                                <div className="text-sm mt-1 animate-pulse text-blue-600">
                                                    Processing...
                                                </div>
                                            )}

                                            {/* Sub-content for Reordering */}
                                            {step.id === 'reordering' && isCompleted && state.semantic_groups && (
                                                <div className="mt-1 flex flex-wrap gap-1">
                                                    {state.semantic_groups.map((g, i) => (
                                                        <span key={i} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                                                            {g.group_name} ({g.chunk_ids.length})
                                                        </span>
                                                    ))}
                                                </div>
                                            )}

                                            {/* Sub-content for Planning */}
                                            {step.id === 'planning' && isCompleted && state.queries && (
                                                <div className="mt-1 text-xs text-gray-500 italic truncate">
                                                    Planned {state.queries.length} searches...
                                                </div>
                                            )}
                                        </div>

                                        {/* Animated Background for Current Step */}
                                        {isCurrentPending && (
                                            <div className="absolute inset-0 rounded-lg bg-gradient-to-r animate-pulse from-blue-100/50 to-purple-100/50" />
                                        )}
                                    </div>
                                );
                            })}
                        </div>

                        {/* Decorative Elements */}
                        <div className="absolute top-3 right-3 w-16 h-16 rounded-full blur-xl bg-gradient-to-br from-blue-200/30 to-purple-200/30" />
                        <div className="absolute bottom-3 left-3 w-12 h-12 rounded-full blur-xl bg-gradient-to-br from-green-200/30 to-emerald-200/30" />
                    </div>
                </div>
            );
        }
    });

    return null;
};

// Icons matches example
function CheckIcon() {
    return (
        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
        </svg>
    );
}

function SpinnerIcon() {
    return (
        <svg
            className="w-4 h-4 animate-spin text-white"
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

function ClockIcon() {
    return (
        <svg
            className="w-3 h-3 text-gray-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
        >
            <circle cx="12" cy="12" r="10" strokeWidth="2" />
            <polyline points="12,6 12,12 16,14" strokeWidth="2" />
        </svg>
    );
}

export default RAGStatus;
