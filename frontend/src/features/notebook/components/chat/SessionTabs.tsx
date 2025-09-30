import React, { useState, useRef } from 'react';
import { Plus, X, Edit3, MessageCircle, Clock, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';
import { Badge } from '@/shared/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/shared/components/ui/tooltip';
import type { SessionTabsProps } from '@/features/notebook/type';

const SessionTabs: React.FC<SessionTabsProps> = ({
  sessions,
  activeTabs,
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

  const formatLastActivity = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));

    if (diffInMinutes < 1) return 'now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`;
    return date.toLocaleDateString();
  };

  if (sessions.length === 0) {
    return null;
  }

  return (
    <TooltipProvider>
      <div className="flex items-center bg-white border-b border-gray-200 px-4 py-2 space-x-2 overflow-x-auto scrollbar-thin scrollbar-thumb-gray-300">
        <AnimatePresence>
          {sessions.map((session) => {
            const isActive = session.id === activeSessionId;
            const isEditing = editingSessionId === session.id;

            return (
              <motion.div
                key={session.id}
                initial={{ opacity: 0, scale: 0.95, x: -20 }}
                animate={{ opacity: 1, scale: 1, x: 0 }}
                exit={{ opacity: 0, scale: 0.95, x: -20 }}
                transition={{ duration: 0.2 }}
                className={`flex items-center rounded-lg border transition-all duration-200 min-w-0 ${
                  isActive
                    ? 'bg-red-50 border-red-200 shadow-sm'
                    : 'bg-gray-50 border-gray-200 hover:bg-gray-100 hover:border-gray-300'
                }`}
              >
                <div
                  className={`flex items-center px-3 py-2 cursor-pointer min-w-0 ${
                    isEditing ? 'cursor-default' : ''
                  }`}
                  onClick={() => !isEditing && onSwitchSession(session.id)}
                >
                  {/* Session Icon */}
                  <MessageCircle
                    className={`h-4 w-4 flex-shrink-0 mr-2 ${
                      isActive ? 'text-red-600' : 'text-gray-500'
                    }`}
                  />

                  {/* Session Title / Edit Input */}
                  <div className="flex items-center min-w-0 flex-1">
                    {isEditing ? (
                      <Input
                        ref={editInputRef}
                        value={editingTitle}
                        onChange={(e) => setEditingTitle(e.target.value)}
                        onKeyDown={handleKeyPress}
                        onBlur={handleSaveEdit}
                        className="h-6 px-1 py-0 text-sm border-none bg-transparent focus:ring-1 focus:ring-red-300 min-w-0"
                      />
                    ) : (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span
                            className={`text-sm font-medium truncate max-w-32 ${
                              isActive ? 'text-red-700' : 'text-gray-700'
                            }`}
                            onDoubleClick={() => handleStartEdit(session.id, session.title)}
                          >
                            {session.title}
                          </span>
                        </TooltipTrigger>
                        <TooltipContent>
                          <div className="text-xs space-y-1">
                            <div className="font-medium">{session.title}</div>
                            <div className="text-gray-500 flex items-center space-x-1">
                              <Clock className="h-3 w-3" />
                              <span>{formatLastActivity(session.last_activity)}</span>
                            </div>
                            <div className="text-gray-500">
                              {session.message_count} messages
                            </div>
                          </div>
                        </TooltipContent>
                      </Tooltip>
                    )}
                  </div>

                  {/* Message Count Badge */}
                  {session.message_count > 0 && !isEditing && (
                    <Badge
                      variant="secondary"
                      className={`ml-2 h-5 px-1.5 text-xs ${
                        isActive
                          ? 'bg-red-100 text-red-700 border-red-200'
                          : 'bg-gray-200 text-gray-600 border-gray-300'
                      }`}
                    >
                      {session.message_count}
                    </Badge>
                  )}
                </div>

                {/* Tab Actions */}
                {!isEditing && (
                  <div className="flex items-center pl-1 pr-2 space-x-1">
                    {/* Edit Button */}
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 hover:bg-red-100/50"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleStartEdit(session.id, session.title);
                          }}
                        >
                          <Edit3 className="h-3 w-3" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>
                        <span>Rename session</span>
                      </TooltipContent>
                    </Tooltip>

                    {/* Close Button */}
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 hover:bg-red-100 hover:text-red-700"
                          onClick={(e) => {
                            e.stopPropagation();
                            onCloseSession(session.id);
                          }}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>
                        <span>Close session</span>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                )}
              </motion.div>
            );
          })}
        </AnimatePresence>

        {/* Add New Tab Button */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0 flex-shrink-0 hover:bg-red-50 hover:text-red-600 border-2 border-dashed border-gray-300 hover:border-red-300 transition-colors"
              onClick={onCreateSession}
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <span>New chat session</span>
          </TooltipContent>
        </Tooltip>

        {/* Session Count Indicator */}
        {sessions.length > 3 && (
          <div className="flex items-center pl-2 border-l border-gray-300">
            <span className="text-xs text-gray-500">
              {sessions.length} sessions
            </span>
          </div>
        )}
      </div>
    </TooltipProvider>
  );
};

export default SessionTabs;
