import React, { useState, useEffect } from "react";
import { BookOpen, Calendar, Edit3, ChevronDown } from "lucide-react";
import type { Notebook } from "@/shared/api";
import DeleteConfirmationDialog from "@/shared/components/ui/DeleteConfirmationDialog";
import NotebookActions from "@/features/notebook/components/shared/NotebookActions";

interface NotebookListProps {
  notebooks: Notebook[];
  onNotebookClick: (notebook: Notebook) => void;
  onDeleteNotebook: (notebookId: string) => Promise<void>;
  formatDate: (date: string) => string;
}

/**
 * List view component for displaying notebooks
 * Shows notebooks in a detailed list format
 */
const NotebookList: React.FC<NotebookListProps> = ({ notebooks, onNotebookClick, onDeleteNotebook, formatDate }) => {
  const [showDeleteDialog, setShowDeleteDialog] = useState<Notebook | null>(null);

  const handleDeleteClick = (notebook: Notebook) => {
    setShowDeleteDialog(notebook);
  };

  const handleConfirmDelete = async () => {
    if (showDeleteDialog) {
      await onDeleteNotebook(showDeleteDialog.id);
      setShowDeleteDialog(null);
    }
  };

  const handleCancelDelete = () => {
    setShowDeleteDialog(null);
  };

  // Dropdown handling is encapsulated in NotebookActions
  return (
    <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
      <div className="divide-y divide-gray-100">
        {notebooks.map((notebook) => (
          <div
            key={notebook.id}
            onClick={() => onNotebookClick(notebook)}
            className="group p-6 hover:bg-gray-50 cursor-pointer transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4 flex-1">
                <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                  <BookOpen className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-gray-900 group-hover:text-red-600 transition-colors">
                    {notebook.name}
                  </h3>
                  {notebook.description && (
                    <p className="text-gray-600 text-sm mt-1 truncate">
                      {notebook.description}
                    </p>
                  )}
                  <div className="flex items-center text-xs text-gray-500 mt-2 space-x-4">
                    <div className="flex items-center space-x-1">
                      <Calendar className="w-3 h-3" />
                      <span>Created {formatDate(notebook.created_at)}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <NotebookActions onDelete={() => handleDeleteClick(notebook)} />
                <ChevronDown className="w-5 h-5 text-gray-400 rotate-90 group-hover:text-red-500 transition-colors" />
              </div>
            </div>
          </div>
        ))}
      </div>
      
      <DeleteConfirmationDialog
        isOpen={!!showDeleteDialog}
        title="Delete Notebook"
        message={showDeleteDialog ? `Are you sure you want to delete "${showDeleteDialog.name}"? This action cannot be undone and will delete all associated data including reports and podcasts.` : ''}
        onCancel={handleCancelDelete}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
};

export default NotebookList;
