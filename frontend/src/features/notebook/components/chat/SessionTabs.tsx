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
  hasFiles = false,
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
      <div className="flex items-center bg-white px-6 gap-2 overflow-x-auto scrollbar-hide border-b border-[#F7F7F7]">
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
                transition={{ duration: 0.3 }}
                className={`group relative flex items-center gap-2 px-1 py-3 cursor-pointer transition-colors ${isActive
                    ? 'text-[#1E1E1E]'
                    : 'text-[#666666] hover:text-[#1E1E1E]'
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
                    className="h-6 px-1 py-0 text-[14px] border-none bg-transparent focus:ring-0 min-w-[100px] max-w-[200px] font-medium"
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <span
                    className={`text-[14px] font-medium truncate max-w-[200px] ${isActive ? 'font-bold' : ''}`}
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
                    className={`h-4 w-4 p-0 rounded-full hover:bg-[#F5F5F5] transition-opacity ${isActive ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                      }`}
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      onCloseSession(session.id);
                    }}
                  >
                    <X className="h-3 w-3 text-[#666666]" />
                  </Button>
                )}

                {/* Active Indicator - Underline */}
                {isActive && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#CE0E2D]"
                    transition={{ type: "spring", duration: 0.3 }}
                  />
                )}
              </motion.div>
            );
          })}
        </AnimatePresence>

        {/* Add New Tab Button */}
        <Button
          variant="ghost"
          size="sm"
          className="flex-shrink-0 h-8 px-3 text-[12px] font-medium text-[#666666] hover:text-[#1E1E1E] hover:bg-[#F5F5F5] rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed ml-2"
          onClick={onCreateSession}
          disabled={isLoading || !hasFiles}
          title={!hasFiles ? "Upload and parse at least one source to enable chat" : ""}
        >
          {isLoading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
          ) : (
            <Plus className="h-3.5 w-3.5 mr-1.5" />
          )}
          New Chat
        </Button>
      </div>
    </TooltipProvider>
  );
};

export default SessionTabs;
