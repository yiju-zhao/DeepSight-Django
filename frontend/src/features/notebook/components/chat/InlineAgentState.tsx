/**
 * Inline Agent State Component
 *
 * Displays minimal agent execution progress in the chat interface with expandable details.
 * Shows current step, progress bar, and key metrics.
 */

import { useState } from 'react';
import { ChevronDown, ChevronUp, Loader2, CheckCircle } from 'lucide-react';
import { RAGAgentState, STEP_LABELS, getProgressPercentage } from '../../types/agent';

interface InlineAgentStateProps {
  state: RAGAgentState;
}

export function InlineAgentState({ state }: InlineAgentStateProps) {
  const [expanded, setExpanded] = useState(false);

  // Don't render if agent is idle
  if (state.current_step === 'idle') {
    return null;
  }

  const isComplete = state.current_step === 'complete';
  const isProcessing = !isComplete;
  const progress = getProgressPercentage(state);

  return (
    <div className="inline-agent-state">
      {/* Header with status icon and label */}
      <div className="progress-header">
        {isProcessing ? (
          <Loader2 className="animate-spin text-blue-500" size={16} />
        ) : (
          <CheckCircle className="text-green-500" size={16} />
        )}
        <span className="step-label">
          {state.agent_reasoning || STEP_LABELS[state.current_step]}
        </span>
        <button
          onClick={() => setExpanded(!expanded)}
          className="expand-button"
          aria-label={expanded ? 'Collapse details' : 'Expand details'}
        >
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      {/* Progress Bar */}
      <div className="progress-bar">
        <div
          className="progress-fill"
          style={{ width: `${progress}%` }}
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="expanded-details">
          <div className="stat">
            <span>Iterations:</span>
            <span className="stat-value">{state.iteration_count}</span>
          </div>
          <div className="stat">
            <span>Documents Retrieved:</span>
            <span className="stat-value">{state.retrieved_chunks.length}</span>
          </div>
          {state.graded_documents.length > 0 && (
            <div className="stat">
              <span>Relevant Docs:</span>
              <span className="stat-value">
                {state.graded_documents.filter(d => d.relevant).length} / {state.graded_documents.length}
              </span>
            </div>
          )}
          {state.query_rewrites.length > 0 && (
            <div className="stat">
              <span>Query Rewrites:</span>
              <span className="stat-value">{state.query_rewrites.length}</span>
            </div>
          )}
          {state.total_tool_calls > 0 && (
            <div className="stat">
              <span>Tool Calls:</span>
              <span className="stat-value">{state.total_tool_calls}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
