import React from 'react';
import { useCoAgentStateRender } from "@copilotkit/react-core";
import { Loader2, Database, BookOpen, Layers, CheckCircle } from 'lucide-react';

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

const RAGStatus: React.FC = () => {
    useCoAgentStateRender<RAGAgentState>({
        name: "rag_agent", // Must match backend agent name
        render: ({ state }) => {
            // Only render if we are in an active RAG process or have results
            if (!state.current_step && !state.generation) return null;

            const step = state.current_step || 'idle';
            const isAnalyzing = step === 'analyzing';
            const isRetrieving = step === 'retrieving';
            const isReordering = step === 'reordering';
            const isGenerating = step === 'synthesizing';
            const isComplete = !!state.generation && step === 'synthesizing'; // generation done

            return (
                <div className="mx-6 my-4 p-4 bg-white border border-gray-100 rounded-xl shadow-sm max-w-2xl">
                    <div className="space-y-4">
                        {/* Header Status */}
                        <div className="flex items-center gap-2 mb-2">
                            <StatusIcon step={step} />
                            <span className="font-semibold text-gray-700 capitalize">
                                {step === 'analyzing' && 'Analyzing Request...'}
                                {step === 'retrieving' && 'Searching Documents...'}
                                {step === 'reordering' && 'Organizing Information...'}
                                {step === 'synthesizing' && 'Generating Answer...'}
                                {!['analyzing', 'retrieving', 'reordering', 'synthesizing'].includes(step) && 'Ready'}
                            </span>
                        </div>

                        {/* Queries Section */}
                        {state.queries && state.queries.length > 0 && (
                            <div className="pl-8 border-l-2 border-gray-100 ml-3">
                                <p className="text-xs font-medium text-gray-500 mb-1">Search Plan</p>
                                <ul className="space-y-1">
                                    {state.queries.map((q, i) => (
                                        <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                                            <span className="text-blue-400 mt-1">•</span>
                                            {q}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {/* Semantic Groups Section (Result of Reordering) */}
                        {state.semantic_groups && state.semantic_groups.length > 0 && (
                            <div className="pl-8 border-l-2 border-blue-100 ml-3 transition-all duration-500">
                                <p className="text-xs font-medium text-blue-600 mb-2 flex items-center gap-1">
                                    <Layers className="h-3 w-3" />
                                    Structured Knowledge Groups
                                </p>
                                <div className="grid gap-2">
                                    {state.semantic_groups.map((group, i) => (
                                        <div key={i} className="bg-blue-50/50 p-2 rounded border border-blue-100/50">
                                            <div className="font-medium text-sm text-gray-800">{group.group_name}</div>
                                            <div className="text-xs text-gray-500 mt-0.5">{group.description}</div>
                                            <div className="text-[10px] text-gray-400 mt-1">
                                                {group.chunk_ids.length} source{group.chunk_ids.length !== 1 ? 's' : ''}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            );
        }
    });

    return null; // The hook renders the UI via the render prop, so this component returns null in the tree
};

const StatusIcon = ({ step }: { step: string }) => {
    switch (step) {
        case 'analyzing':
            return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
        case 'retrieving':
            return <Database className="h-5 w-5 text-purple-500 animate-pulse" />;
        case 'reordering':
            return <Layers className="h-5 w-5 text-orange-500 animate-pulse" />;
        case 'synthesizing':
            return <BookOpen className="h-5 w-5 text-green-500 animate-bounce" />;
        default:
            return <CheckCircle className="h-5 w-5 text-gray-300" />;
    }
};

export default RAGStatus;
