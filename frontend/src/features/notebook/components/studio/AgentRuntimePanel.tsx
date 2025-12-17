/**
 * Agent Runtime Panel Component
 *
 * Displays detailed agent execution state in the studio panel.
 * Shows comprehensive information about retrieval, grading, rewrites, and synthesis.
 */

import { FileText, CheckCircle, XCircle, RefreshCw, Activity } from 'lucide-react';
import { RAGAgentState, STEP_LABELS } from '../../types/agent';

interface AgentRuntimePanelProps {
  state: RAGAgentState;
}

export function AgentRuntimePanel({ state }: AgentRuntimePanelProps) {
  if (state.current_step === 'idle') {
    return (
      <div className="agent-runtime-panel empty">
        <Activity size={48} className="empty-icon" />
        <p className="empty-message">No active agent execution</p>
        <p className="empty-hint">Agent runtime states will appear here during chat</p>
      </div>
    );
  }

  return (
    <div className="agent-runtime-panel">
      {/* Execution Overview */}
      <section className="execution-overview">
        <h3 className="section-title">Execution Status</h3>
        <div className="status-grid">
          <div className="stat-card">
            <span className="label">Current Step</span>
            <span className="value">{STEP_LABELS[state.current_step]}</span>
          </div>
          <div className="stat-card">
            <span className="label">Iterations</span>
            <span className="value">{state.iteration_count}</span>
          </div>
          <div className="stat-card">
            <span className="label">Tool Calls</span>
            <span className="value">{state.total_tool_calls}</span>
          </div>
        </div>
        {state.agent_reasoning && (
          <div className="reasoning">
            <strong>Agent Reasoning:</strong>
            <p>{state.agent_reasoning}</p>
          </div>
        )}
      </section>

      {/* Retrieved Documents */}
      {(state.retrieved_chunks?.length || 0) > 0 && (
        <section className="retrieved-documents">
          <h3 className="section-title">
            Retrieved Documents ({state.retrieved_chunks?.length})
          </h3>
          <div className="document-list">
            {state.retrieved_chunks?.map((chunk, idx) => (
              <div key={idx} className="document-card">
                <div className="header">
                  <FileText size={16} className="icon" />
                  <span className="doc-name">{chunk.document_name}</span>
                  {chunk.score > 0 && (
                    <span className="score">Score: {chunk.score.toFixed(3)}</span>
                  )}
                </div>
                <p className="content-preview">
                  {chunk.content.substring(0, 200)}
                  {chunk.content.length > 200 && '...'}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Graded Documents */}
      {(state.graded_documents?.length || 0) > 0 && (
        <section className="graded-documents">
          <h3 className="section-title">Grading Results</h3>
          <div className="grading-stats">
            <span className="relevant">
              ✓ {state.graded_documents?.filter(d => d.relevant).length} Relevant
            </span>
            <span className="not-relevant">
              ✗ {state.graded_documents?.filter(d => !d.relevant).length} Not Relevant
            </span>
          </div>
          <div className="document-list">
            {state.graded_documents?.map((doc, idx) => (
              <div
                key={idx}
                className={`document-card ${doc.relevant ? 'relevant' : 'not-relevant'}`}
              >
                <div className="header">
                  {doc.relevant ? (
                    <CheckCircle className="icon text-green-500" size={16} />
                  ) : (
                    <XCircle className="icon text-red-500" size={16} />
                  )}
                  <span className="verdict">
                    {doc.relevant ? 'Relevant' : 'Not Relevant'}
                  </span>
                  {doc.score > 0 && (
                    <span className="score">Score: {doc.score.toFixed(3)}</span>
                  )}
                </div>
                <p className="reason">{doc.reason}</p>
                <p className="content-preview">
                  {doc.content.substring(0, 150)}
                  {doc.content.length > 150 && '...'}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Query Rewrites */}
      {(state.query_rewrites?.length || 0) > 0 && (
        <section className="query-rewrites">
          <h3 className="section-title">
            Query Rewrites ({state.query_rewrites?.length})
          </h3>
          <div className="rewrite-list">
            {state.query_rewrites?.map((query, idx) => (
              <div key={idx} className="rewrite-item">
                <RefreshCw size={14} className="icon" />
                <span className="iteration">Iteration {idx + 1}:</span>
                <p className="query">{query}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Synthesis Progress */}
      {state.current_step === 'synthesizing' && (
        <section className="synthesis-progress">
          <h3 className="section-title">Synthesis Progress</h3>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${state.synthesis_progress}%` }}
              role="progressbar"
              aria-valuenow={state.synthesis_progress}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
          <span className="percentage">{state.synthesis_progress}%</span>
        </section>
      )}
    </div>
  );
}
