/**
 * Agent State Management
 *
 * Provides React context and hooks for managing RAG agent state across the application.
 * State is synchronized from SSE events emitted by the backend during agent execution.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { RAGAgentState, INITIAL_RAG_STATE } from '../types/agent';

interface AgentStateContextValue {
  state: RAGAgentState;
  updateState: (newState: Partial<RAGAgentState>) => void;
  resetState: () => void;
}

const AgentStateContext = createContext<AgentStateContextValue | null>(null);

/**
 * Provider component for agent state
 */
export function AgentStateProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<RAGAgentState>(INITIAL_RAG_STATE);

  const updateState = useCallback((newState: Partial<RAGAgentState>) => {
    setState(prevState => ({
      ...prevState,
      ...newState
    }));
  }, []);

  const resetState = useCallback(() => {
    setState(INITIAL_RAG_STATE);
  }, []);

  return (
    <AgentStateContext.Provider value={{ state, updateState, resetState }}>
      {children}
    </AgentStateContext.Provider>
  );
}

/**
 * Hook to access agent state
 */
export function useAgentState() {
  const context = useContext(AgentStateContext);
  if (!context) {
    throw new Error('useAgentState must be used within AgentStateProvider');
  }
  return context;
}

/**
 * Hook to synchronize agent state from SSE events
 *
 * Listens to server-sent events and updates the agent state in real-time.
 * Should be used in the chat component that handles the SSE connection.
 *
 * @param onStateUpdate - Callback to receive agent_state events from SSE
 */
export function useAgentStateSync(onStateUpdate: ((state: RAGAgentState) => void) | null) {
  const { updateState, resetState } = useAgentState();

  useEffect(() => {
    if (!onStateUpdate) return;

    // Provide the update function to the parent component
    // The parent handles the SSE connection and calls this when agent_state events arrive
    onStateUpdate(updateState as any);

    // Reset state when component unmounts
    return () => {
      resetState();
    };
  }, [onStateUpdate, updateState, resetState]);
}

/**
 * Parse agent_state event from SSE and update context
 *
 * Use this helper in your SSE event handler:
 *
 * @example
 * eventSource.addEventListener('message', (event) => {
 *   const data = JSON.parse(event.data);
 *   if (data.type === 'agent_state') {
 *     handleAgentStateEvent(data.state, updateAgentState);
 *   }
 * });
 */
export function handleAgentStateEvent(
  stateData: any,
  updateState: (state: Partial<RAGAgentState>) => void
) {
  // Validate and update state
  if (!stateData) return;

  updateState({
    current_step: stateData.current_step || 'idle',
    iteration_count: stateData.iteration_count || 0,
    graded_documents: stateData.graded_documents || [],
    query_rewrites: stateData.query_rewrites || [],
    synthesis_progress: stateData.synthesis_progress || 0,
    total_tool_calls: stateData.total_tool_calls || 0,
    agent_reasoning: stateData.agent_reasoning || '',
    retrieved_chunks: stateData.retrieved_chunks || []
  });
}
