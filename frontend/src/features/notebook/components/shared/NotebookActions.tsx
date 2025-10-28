import React, { useState, useEffect, useCallback } from 'react';
import { MoreVertical, Trash2 } from 'lucide-react';

interface NotebookActionsProps {
  onDelete: () => void;
}

export const NotebookActions: React.FC<NotebookActionsProps> = ({ onDelete }) => {
  const [open, setOpen] = useState(false);

  const toggle = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setOpen((v) => !v);
  }, []);

  useEffect(() => {
    if (!open) return;
    const handler = () => setOpen(false);
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, [open]);

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete();
    setOpen(false);
  };

  return (
    <div className="relative">
      <button onClick={toggle} className="opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-gray-100 transition-all">
        <MoreVertical className="w-4 h-4 text-gray-400" />
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-10">
          <div className="py-1">
            <button
              onClick={handleDelete}
              className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center space-x-2"
            >
              <Trash2 className="w-4 h-4" />
              <span>Delete notebook</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotebookActions;

