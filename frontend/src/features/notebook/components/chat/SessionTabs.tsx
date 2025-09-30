import React, { useState, useRef } from 'react';
import { Plus, X, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';
import { TooltipProvider } from '@/shared/components/ui/tooltip';
import type { SessionTabsProps } from '@/features/notebook/type';

const SessionTabs: React.FC<SessionTabsProps> = ({
  sessions,
  activeSessionId,
  onCreateSession,
  onSwitchSession,
  onCloseSession,
  onUpdateTitle,
  isLoading = false,
}) => {
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const editInputRef = useRef<HTMLInputElement>(null);

  const handleStartEdit = (sessionId: string, currentTitle: string) => {
    setEditingSessionId(sessionId);
    setEditingTitle(currentTitle);
    setTimeout(() => {
      editInputRef.current?.focus();
      editInputRef.current?.select();
    }, 0);
  };

  const handleSaveEdit = () => {
    if (editingSessionId && editingTitle.trim()) {
      onUpdateTitle(editingSessionId, editingTitle.trim());
    }
    setEditingSessionId(null);
    setEditingTitle('');
  };

  const handleCancelEdit = () => {
    setEditingSessionId(null);
    setEditingTitle('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSaveEdit();
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  if (sessions.length === 0) {
    return null;
  }

  return (
    <TooltipProvider>
      <div className="flex items-end bg-gray-50 px-2 gap-0.5 overflow-x-auto scrollbar-thin scrollbar-thumb-gray-300 border-b border-gray-200">
        <AnimatePresence>
          {sessions.map((session) => {
            const isActive = session.id === activeSessionId;
            const isEditing = editingSessionId === session.id;

            return (
              <motion.div
                key={session.id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.15 }}
                className={`group flex items-center gap-1.5 px-3 py-1.5 rounded-t-lg cursor-pointer transition-all ${
                  isActive
                    ? 'bg-white border-t border-x border-gray-200'
                    : 'bg-gray-100 hover:bg-gray-200'
                }`}
                onClick={() => !isEditing && onSwitchSession(session.id)}
              >
                {/* Session Title / Edit Input */}
                {isEditing ? (
                  <Input
                    ref={editInputRef}
                    value={editingTitle}
                    onChange={(e) => setEditingTitle(e.target.value)}
                    onKeyDown={handleKeyPress}
                    onBlur={handleSaveEdit}
                    className="h-6 px-1 py-0 text-sm border-none bg-transparent focus:ring-1 focus:ring-red-300 min-w-[100px] max-w-[200px]"
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <span
                    className={`text-sm font-medium truncate max-w-[200px] ${
                      isActive ? 'text-gray-900' : 'text-gray-600'
                    }`}
                    onDoubleClick={(e) => {
                      e.stopPropagation();
                      handleStartEdit(session.id, session.title);
                    }}
                  >
                    {session.title}
                  </span>
                )}

                {/* Close Button */}
                {!isEditing && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className={`h-5 w-5 p-0 rounded hover:bg-gray-300 transition-opacity ${
                      isActive ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                    }`}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (window.confirm(`Close "${session.title}"?`)) {
                        onCloseSession(session.id);
                      }
                    }}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                )}
              </motion.div>
            );
          })}
        </AnimatePresence>

        {/* Add New Tab Button */}
        <Button
          variant="ghost"
          size="sm"
          className="flex-shrink-0 h-7 px-3 mb-0.5 text-xs font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-200 rounded-t-lg transition-colors"
          onClick={onCreateSession}
          disabled={isLoading}
        >
          {isLoading ? (
            <Loader2 className="h-3 w-3 animate-spin mr-1.5" />
          ) : (
            <Plus className="h-3 w-3 mr-1.5" />
          )}
          New
        </Button>
      </div>
    </TooltipProvider>
  );
};

export default SessionTabs;
