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
            <div className="flex justify-between items-start mb-2">
                <h4 className="font-semibold text-gray-900 line-clamp-1 flex-1 pr-8 text-[15px]">
                    {item.title || 'Untitled Note'}
                </h4>

                {/* Action Buttons (visible on hover) */}
                <div className="absolute top-4 right-4 flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity bg-white pl-2">
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
                    <Pin className="h-3.5 w-3.5 text-accent-red absolute top-4 right-4" />
                )}
                {isPinned && onPin && (
                    <Pin className="h-3.5 w-3.5 text-accent-red absolute top-4 right-4 group-hover:opacity-0 transition-opacity" />
                )}
            </div>

            <div className="text-sm text-gray-600 line-clamp-3 mb-3 min-h-[1.25rem] prose prose-sm prose-gray max-w-none [&_p]:my-0 [&_ul]:my-0 [&_ol]:my-0 [&_h1]:text-sm [&_h2]:text-sm [&_h3]:text-sm [&_h1]:font-semibold [&_h2]:font-semibold [&_h3]:font-semibold [&_h1]:my-0 [&_h2]:my-0 [&_h3]:my-0">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {item.content || 'No content'}
                </ReactMarkdown>
            </div>

            <div className="flex items-center justify-between text-xs text-gray-400 mt-2">
                <div className="flex items-center gap-2">
                    <span className="flex items-center">
                        <Calendar className="h-3 w-3 mr-1" />
                        {item.createdAt ? formatDistanceToNow(new Date(item.createdAt), { addSuffix: true }) : ''}
                    </span>
                </div>
            </div>

            {item.tags && item.tags.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1">
                    {item.tags.slice(0, 3).map((tag, i) => (
                        <Badge key={i} variant="secondary" className="bg-gray-100 text-gray-600 hover:bg-gray-200 text-[10px] py-0 h-5 font-normal px-2">
                            <Tag className="h-2.5 w-2.5 mr-1 opacity-70" />
                            {tag}
                        </Badge>
                    ))}
                    {item.tags.length > 3 && (
                        <span className="text-[10px] text-gray-400 ml-1">+{item.tags.length - 3}</span>
                    )}
                </div>
            )}
        </div>
    );
};

export default NoteCard;
