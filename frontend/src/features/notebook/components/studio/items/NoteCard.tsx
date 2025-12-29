import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { Trash2, Pin, PinOff, Calendar, Tag } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/shared/components/ui/button';
import { Badge } from '@/shared/components/ui/badge';
import type { NoteStudioItem } from '../../../types/studioItem';

interface NoteCardProps {
    item: NoteStudioItem;
    className?: string;
    onSelect: (item: NoteStudioItem) => void;
    onDelete: (item: NoteStudioItem) => void;
    onPin?: (item: NoteStudioItem) => void; // Optional for now
}

const NoteCard: React.FC<NoteCardProps> = ({ item, className, onSelect, onDelete, onPin }) => {
    // Mock pin state since NoteStudioItem doesn't have is_pinned yet? 
    // Wait, I should add is_pinned to NoteStudioItem if I want to support it. 
    // For now let's assume item might have it or we ignore pinning in the unified list or just show it if present.
    // The adapter currently doesn't map is_pinned. Let's start basic.

    const isPinned = (item as any).is_pinned || false;

    return (
        <div
            className={`group relative bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer ${className}`}
            onClick={() => onSelect(item)}
        >
            {/* Action Buttons (visible on hover) - Positioned absolute to not take space */}
            <div className="absolute top-2 right-8 flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity bg-white/80 backdrop-blur-sm pl-2 pr-1 rounded-l-md z-30">
                {onPin && (
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0 hover:bg-gray-100 text-gray-500"
                        onClick={(e) => {
                            e.stopPropagation();
                            onPin(item);
                        }}
                        title={isPinned ? "Unpin note" : "Pin note"}
                    >
                        {isPinned ? <PinOff className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}
                    </Button>
                )}
                <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0 hover:bg-red-50 text-gray-500 hover:text-red-600"
                    onClick={(e) => {
                        e.stopPropagation();
                        onDelete(item);
                    }}
                    title="Delete note"
                >
                    <Trash2 className="h-3.5 w-3.5" />
                </Button>
            </div>

            {/* Persistent Pin Icon (hidden on hover when buttons appear) */}
            {isPinned && !onPin && (
                <Pin className="h-3.5 w-3.5 text-accent-red absolute top-3 right-8 z-20" />
            )}
            {isPinned && onPin && (
                <Pin className="h-3.5 w-3.5 text-accent-red absolute top-3 right-8 z-20 group-hover:opacity-0 transition-opacity" />
            )}

            <div className="text-sm text-gray-600 line-clamp-4 mb-3 min-h-[1.5rem] prose prose-sm prose-gray max-w-none [&_p]:my-0 [&_ul]:my-0 [&_ol]:my-0 [&_h1]:text-sm [&_h2]:text-sm [&_h3]:text-sm [&_h1]:font-semibold [&_h2]:font-semibold [&_h3]:font-semibold [&_h1]:my-0 [&_h2]:my-0 [&_h3]:my-0 pt-1">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {item.content || 'No content'}
                </ReactMarkdown>
            </div>

            <div className="flex items-center justify-between text-xs text-gray-400 mt-2 border-t border-gray-50 pt-2">
                <span className="flex items-center flex-shrink-0 mr-2">
                    <Calendar className="h-3 w-3 mr-1" />
                    {item.createdAt ? formatDistanceToNow(new Date(item.createdAt), { addSuffix: true }) : ''}
                </span>

                {item.tags && item.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 justify-end">
                        {item.tags.slice(0, 2).map((tag, i) => (
                            <Badge key={i} variant="secondary" className="bg-gray-100 text-gray-500 text-[9px] py-0 h-4 font-normal px-1.5">
                                {tag}
                            </Badge>
                        ))}
                        {item.tags.length > 2 && (
                            <span className="text-[9px] text-gray-400 ml-0.5">+{item.tags.length - 2}</span>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default NoteCard;
