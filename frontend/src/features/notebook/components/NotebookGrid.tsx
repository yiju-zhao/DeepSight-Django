import React, { useState, useEffect, useCallback, useMemo } from "react";
import { BookOpen, Calendar } from "lucide-react";
import type { Notebook } from "@/shared/api";
import DeleteConfirmationDialog from "@/shared/components/ui/DeleteConfirmationDialog";
import NotebookActions from "@/features/notebook/components/shared/NotebookActions";

interface NotebookGridProps {
  notebooks: Notebook[];
  onNotebookClick: (notebook: Notebook) => void;
  onDeleteNotebook: (notebookId: string) => Promise<void>;
  formatDate: (date: string) => string;
}

/**
 * Grid view component for displaying notebooks
 * Shows notebooks in a responsive card grid layout
 * Optimized with React.memo, useCallback and useMemo for performance
 */
const NotebookGrid: React.FC<NotebookGridProps> = React.memo(({ notebooks, onNotebookClick, onDeleteNotebook, formatDate }) => {
  const [showDeleteDialog, setShowDeleteDialog] = useState<Notebook | null>(null);

  const handleDeleteClick = useCallback((notebook: Notebook) => {
    setShowDeleteDialog(notebook);
  }, []);

  const handleConfirmDelete = useCallback(async () => {
    if (showDeleteDialog) {
      await onDeleteNotebook(showDeleteDialog.id);
      setShowDeleteDialog(null);
    }
  }, [showDeleteDialog, onDeleteNotebook]);

  const handleCancelDelete = useCallback(() => {
    setShowDeleteDialog(null);
  }, []);

  // Dropdown handling is encapsulated in NotebookActions
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {notebooks.map((notebook) => (
        <div
          key={notebook.id}
          onClick={() => onNotebookClick(notebook)}
          className="group bg-white rounded-2xl border border-gray-200 hover:border-red-300 p-6 cursor-pointer transition-all duration-200 hover:shadow-xl hover:-translate-y-1"
        >
          <div className="flex items-start justify-between mb-4">
            <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
              <BookOpen className="w-5 h-5 text-white" />
            </div>
            <NotebookActions onDelete={() => handleDeleteClick(notebook)} />
          </div>
          
          <h3 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-red-600 transition-colors">
            {notebook.name}
          </h3>
          
          {notebook.description && (
            <p className="text-gray-600 text-sm mb-4 line-clamp-2">
              {notebook.description}
            </p>
          )}
          
          <div className="flex items-center text-xs text-gray-500 space-x-4">
            <div className="flex items-center space-x-1">
              <Calendar className="w-3 h-3" />
              <span>{formatDate(notebook.created_at)}</span>
            </div>
          </div>
        </div>
      ))}
      
      <DeleteConfirmationDialog
        isOpen={!!showDeleteDialog}
        title="Delete Notebook"
        message={showDeleteDialog ? `Are you sure you want to delete "${showDeleteDialog.name}"? This action cannot be undone and will delete all associated data including reports and podcasts.` : ''}
        onCancel={handleCancelDelete}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
});

NotebookGrid.displayName = 'NotebookGrid';

export default NotebookGrid;
