import React, { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { Trash2, Pin, PinOff, FileText, Calendar, Tag } from 'lucide-react';
import { useNotes } from '@/features/notebook/hooks/notes/useNotes';
import { Button } from '@/shared/components/ui/button';
import { Badge } from '@/shared/components/ui/badge';
import { DeleteConfirmationDialog } from '@/shared/components/ui/DeleteConfirmationDialog';
import { useToast } from '@/shared/components/ui/use-toast';

interface NotesListProps {
    notebookId: string;
    onSelectNote?: (noteId: number) => void;
}

const NotesList: React.FC<NotesListProps> = ({ notebookId, onSelectNote }) => {
    const { notes, isLoading, deleteNote, pinNote, unpinNote } = useNotes(notebookId);
    const { toast } = useToast();
    const [deleteId, setDeleteId] = useState<number | null>(null);

    // Filter and Sort: Pinned first, then by date desc
    const sortedNotes = React.useMemo(() => {
        return [...notes].sort((a, b) => {
            // Pinned notes first
            if (a.is_pinned && !b.is_pinned) return -1;
            if (!a.is_pinned && b.is_pinned) return 1;
            // Then strict reverse chronological
            return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        });
    }, [notes]);

    const handleDelete = async () => {
        if (deleteId) {
            const success = await deleteNote(deleteId);
            if (success) {
                toast({ title: 'Note deleted' });
            } else {
                toast({ title: 'Failed to delete note', variant: 'destructive' });
            }
            setDeleteId(null);
        }
    };

    const handleTogglePin = async (e: React.MouseEvent, note: any) => {
        e.stopPropagation();
        if (note.is_pinned) {
            await unpinNote(note.id);
        } else {
            await pinNote(note.id);
        }
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-40">
                <div className="w-6 h-6 border-2 border-accent-red border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    if (notes.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-full p-8 text-center text-gray-500">
                <div className="bg-gray-100 p-4 rounded-full mb-4">
                    <FileText className="h-8 w-8 text-gray-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No notes yet</h3>
                <p className="text-sm max-w-[200px] mx-auto">Save important chat messages to create notes, or create one manually.</p>
            </div>
        );
    }

    return (
        <div className="space-y-4 p-4 overflow-y-auto max-h-full scrollbar-thin scrollbar-thumb-gray-200">
            {sortedNotes.map((note) => (
                <div
                    key={note.id}
                    className="group relative bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => onSelectNote?.(note.id)}
                >
                    <div className="flex justify-between items-start mb-2">
                        <h4 className="font-semibold text-gray-900 line-clamp-1 flex-1 pr-8 text-[15px]">
                            {note.title || 'Untitled Note'}
                        </h4>

                        {/* Action Buttons (visible on hover) */}
                        <div className="absolute top-4 right-4 flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity bg-white pl-2">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 w-7 p-0 hover:bg-gray-100 text-gray-500"
                                onClick={(e) => handleTogglePin(e, note)}
                                title={note.is_pinned ? "Unpin note" : "Pin note"}
                            >
                                {note.is_pinned ? <PinOff className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 w-7 p-0 hover:bg-red-50 text-gray-500 hover:text-red-600"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setDeleteId(note.id);
                                }}
                                title="Delete note"
                            >
                                <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                        </div>

                        {/* Persistent Pin Icon (hidden on hover when buttons appear) */}
                        {note.is_pinned && (
                            <Pin className="h-3.5 w-3.5 text-accent-red absolute top-4 right-4 group-hover:opacity-0 transition-opacity" />
                        )}
                    </div>

                    <p className="text-sm text-gray-600 line-clamp-3 mb-3 min-h-[1.25rem]">
                        {note.content_preview || 'No content'}
                    </p>

                    <div className="flex items-center justify-between text-xs text-gray-400 mt-2">
                        <div className="flex items-center gap-2">
                            <span className="flex items-center">
                                <Calendar className="h-3 w-3 mr-1" />
                                {formatDistanceToNow(new Date(note.created_at), { addSuffix: true })}
                            </span>
                        </div>
                    </div>

                    {note.tags && note.tags.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1">
                            {note.tags.slice(0, 3).map((tag, i) => (
                                <Badge key={i} variant="secondary" className="bg-gray-100 text-gray-600 hover:bg-gray-200 text-[10px] py-0 h-5 font-normal px-2">
                                    <Tag className="h-2.5 w-2.5 mr-1 opacity-70" />
                                    {tag}
                                </Badge>
                            ))}
                            {note.tags.length > 3 && (
                                <span className="text-[10px] text-gray-400 ml-1">+{note.tags.length - 3}</span>
                            )}
                        </div>
                    )}
                </div>
            ))}

            <DeleteConfirmationDialog
                isOpen={!!deleteId}
                title="Delete Note"
                message="Are you sure you want to delete this note? This action cannot be undone."
                onConfirm={handleDelete}
                onCancel={() => setDeleteId(null)}
            />
        </div>
    );
};

export default NotesList;
