import React, { useEffect, useState, useRef, useMemo } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "@/shared/hooks/useAuth";
import { useNotebook } from "@/features/notebook/queries";
import { useApiUtils } from "@/features/notebook/hooks";
import NotebookLayout from "@/features/notebook/components/layout/NotebookLayout";
import SourcesPanel from "@/features/notebook/components/panels/SourcesPanel";
import SessionChatPanel from "@/features/notebook/components/panels/SessionChatPanel";
import StudioPanel from "@/features/notebook/components/panels/StudioPanel";
import AppLayout from "@/shared/components/layout/AppLayout";
import "highlight.js/styles/github.css";

/**
 * DeepdivePage component
 * Uses extracted hooks and layout components following SOLID principles
 */
export default function DeepdivePage() {
  const { notebookId } = useParams();
  const { isAuthenticated, authChecked } = useAuth();
  const { primeCsrfToken } = useApiUtils();

  // Use TanStack Query for notebook details to avoid duplicate fetches
  const effectiveNotebookId = useMemo(
    () => (authChecked && isAuthenticated && notebookId ? notebookId : ""),
    [authChecked, isAuthenticated, notebookId]
  );
  const { data: currentNotebook, isLoading: loadingNotebook, error: loadError } = useNotebook(
    effectiveNotebookId as string
  );

  // State for component props
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [sourcesRemovedTrigger, setSourcesRemovedTrigger] = useState(0);
  const sourcesListRef = useRef(null);

  // Handler functions
  const handleSelectionChange = () => {
    // Handle selection change logic if needed
  };

  const handleToggleCollapse = () => {
    setIsCollapsed(!isCollapsed);
  };

  const handleOpenModal = (modalType: string, content?: React.ReactElement) => {
    // Handle modal opening logic if needed
  };

  const handleCloseModal = (modalType: string) => {
    // Handle modal closing logic if needed
  };

  const handleSourcesRemoved = () => {
    // Increment trigger to notify components that sources have been removed
    setSourcesRemovedTrigger(prev => prev + 1);
  };

  // Prime CSRF on mount (guard against StrictMode double-invoke)
  const csrfPrimedRef = useRef(false);
  useEffect(() => {
    if (!csrfPrimedRef.current && authChecked && isAuthenticated) {
      csrfPrimedRef.current = true;
      primeCsrfToken();
    }
  }, [authChecked, isAuthenticated, primeCsrfToken]);

  // Remove manual fetch effect; TanStack Query handles fetching and deduping

  // Loading state
  if (!authChecked || loadingNotebook) {
    return (
      <div className="flex items-center justify-center h-screen bg-white">
        <span className="text-gray-500">Loading notebook…</span>
      </div>
    );
  }

  // Error state
  if (loadError) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-white p-4">
        <p className="text-red-600 mb-4">{String(loadError)}</p>
        <div className="space-x-4">
          <button
            onClick={() => window.history.back()}
            className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  // Main render
  if (!notebookId) {
    return (
      <div className="flex items-center justify-center h-screen bg-white">
        <span className="text-red-500">No notebook ID provided</span>
      </div>
    );
  }

  return (
    <AppLayout>
      <NotebookLayout
        notebookId={notebookId}
        notebookTitle={currentNotebook?.name}
        sourcesRemovedTrigger={sourcesRemovedTrigger}
        sourcesPanel={
          <SourcesPanel
            notebookId={notebookId}
            onSelectionChange={handleSelectionChange}
            onToggleCollapse={handleToggleCollapse}
            isCollapsed={isCollapsed}
            onOpenModal={handleOpenModal}
            onCloseModal={handleCloseModal}
            onSourcesRemoved={handleSourcesRemoved}
            ref={sourcesListRef}
          />
        }
        chatPanel={
          <SessionChatPanel
            notebookId={notebookId}
            sourcesListRef={sourcesListRef}
            onSelectionChange={handleSelectionChange}
          />
        }
        studioPanel={
          <StudioPanel
            notebookId={notebookId}
            sourcesListRef={sourcesListRef}
            onSelectionChange={handleSelectionChange}
            onOpenModal={handleOpenModal}
            onCloseModal={handleCloseModal}
          />
        }
      />
    </AppLayout>
  );
}
