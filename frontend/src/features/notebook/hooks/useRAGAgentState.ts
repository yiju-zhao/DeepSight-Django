import { useCoAgent } from "@copilotkit/react-core";
import { useMemo } from "react";

// Define the state interface based on backend RAGAgentState
export interface RAGAgentState {
    current_step?: string;
    semantic_groups?: {
        group_name: string;
        description: string;
        chunk_ids: number[];
    }[];
    queries?: string[];
    generation?: string;
}

export type AgentStep = {
    id: string;
    label: string;
};

export const STEPS_ORDER: AgentStep[] = [
    { id: 'analyzing', label: 'Analyzing Request' },
    { id: 'planning', label: 'Planning Search Strategy' },
    { id: 'retrieving', label: 'Retrieving Documents' },
    { id: 'reordering', label: 'Organizing Information' },
    { id: 'synthesizing', label: 'Generating Answer' }
];

export const useRAGAgentState = () => {
    // Use useCoAgent to access state without automatic chat rendering
    const { state } = useCoAgent<RAGAgentState>({
        name: "rag_agent",
    });

    const currentStepId = state?.current_step || 'idle';

    // Calculate progress
    const progressInfo = useMemo(() => {
        let currentIndex = STEPS_ORDER.findIndex(s => s.id === currentStepId);

        // Map backend step names to display steps if not direct match
        if (currentIndex === -1) {
            const stepMapping: Record<string, number> = {
                'analyzing': 0,
                'planning': 1,
                'retrieving': 2,
                'grade_relevance': 2,
                'grading_relevance': 2,
                'reordering': 3,
                'synthesizing': 4,
                'prepare_generation': 4,
                'completed': 5,
            };
            currentIndex = stepMapping[currentStepId] ?? -1;
        }

        // If completed or have generation with completed status
        if (currentStepId === 'completed' || (state?.generation && currentStepId === 'completed')) {
            currentIndex = STEPS_ORDER.length;
        }

        const percentage = Math.min(((currentIndex) / STEPS_ORDER.length) * 100, 100);

        return {
            currentIndex,
            percentage,
            isCompleted: currentIndex >= STEPS_ORDER.length,
            currentStepLabel: STEPS_ORDER[currentIndex]?.label || 'Processing...'
        };
    }, [currentStepId, state?.generation]);

    return {
        state,
        currentStepId,
        ...progressInfo
    };
};
