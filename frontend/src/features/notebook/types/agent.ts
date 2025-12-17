/**
 * TypeScript types for RAG agent state rendering using CopilotKit AG-UI protocol.
 *
 * These types mirror the backend RAGAgentState defined in Python and enable
 * real-time visualization of agent execution in both inline chat and detailed studio panel views.
 */

export type RAGAgentStep =
  | "idle"
  | "analyzing"
  | "retrieving"
  | "grading"
  | "rewriting"
  | "synthesizing"
  | "complete";

export interface GradedDocument {
  content: string;
  score: number;
  relevant: boolean;
  reason: string;
}

export interface RetrievedChunk {
  content: string;
  score: number;
  document_name: string;
}

export interface RAGAgentState {
  /** Current execution step */
  current_step: RAGAgentStep;

  /** Number of retrieval iterations performed */
  iteration_count: number;

  /** Graded documents with relevance scores and reasons */
  graded_documents: GradedDocument[];

  /** History of query rewrites for improved retrieval */
  query_rewrites: string[];

  /** Synthesis progress percentage (0-100) */
  synthesis_progress: number;

  /** Total number of tool calls made during execution */
  total_tool_calls: number;

  /** Current reasoning or status message for UI display */
  agent_reasoning: string;

  /** Retrieved document chunks from knowledge base */
  retrieved_chunks: RetrievedChunk[];
}

export const INITIAL_RAG_STATE: RAGAgentState = {
  current_step: "idle",
  iteration_count: 0,
  graded_documents: [],
  query_rewrites: [],
  synthesis_progress: 0,
  total_tool_calls: 0,
  agent_reasoning: "",
  retrieved_chunks: []
};

/**
 * Step labels for UI display
 */
export const STEP_LABELS: Record<RAGAgentStep, string> = {
  idle: "Idle",
  analyzing: "Analyzing question...",
  retrieving: "Searching knowledge base...",
  grading: "Evaluating relevance...",
  rewriting: "Refining query...",
  synthesizing: "Generating response...",
  complete: "Complete"
};

/**
 * Calculate progress percentage based on current step
 */
export function getProgressPercentage(state: RAGAgentState): number {
  const stepWeights: Record<RAGAgentStep, number> = {
    idle: 0,
    analyzing: 10,
    retrieving: 30,
    grading: 50,
    rewriting: 60,
    synthesizing: 80 + (state.synthesis_progress * 0.2),
    complete: 100
  };
  return stepWeights[state.current_step] || 0;
}
