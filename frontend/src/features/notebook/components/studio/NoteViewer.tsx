import React, { useState, useEffect } from 'react';
import { X, Edit2, Trash2, Save, ExternalLink, Calendar, Tag, MoreHorizontal } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeHighlight from 'rehype-highlight';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import 'highlight.js/styles/github.css';
import 'katex/dist/katex.min.css';

import { useNotes } from '@/features/notebook/hooks/notes/useNotes';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';
import { Textarea } from '@/shared/components/ui/textarea';
import { Badge } from '@/shared/components/ui/badge';
import { DeleteConfirmationDialog } from '@/shared/components/ui/DeleteConfirmationDialog';
import { useToast } from '@/shared/components/ui/use-toast';
import { useSessionChat } from '@/features/notebook/hooks/chat/useSessionChat';

interface NoteViewerProps {
    notebookId: string;
    noteId: number | null;
    onClose: () => void;
}

const NoteViewer: React.FC<NoteViewerProps> = ({ notebookId, noteId, onClose }) => {
    const { selectedNote, selectNote, updateNote, deleteNote, isLoading } = useNotes(notebookId);
    const { switchSession } = useSessionChat(notebookId);
    const { toast } = useToast();

    const [isEditing, setIsEditing] = useState(false);
    const [editTitle, setEditTitle] = useState('');
    const [editContent, setEditContent] = useState('');
    const [editTags, setEditTags] = useState('');
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

    // Sync prop noteId with hook state
    useEffect(() => {
        selectNote(noteId);
    }, [noteId, selectNote]);

    // Sync local state when note loads
    useEffect(() => {
        if (selectedNote) {
            setEditTitle(selectedNote.title);
            setEditContent(selectedNote.content);
            setEditTags(selectedNote.tags?.join(', ') || '');
        }
    }, [selectedNote]);

    const handleSave = async () => {
        if (!selectedNote) return;

        try {
            const tagsArray = editTags.split(',').map(t => t.trim()).filter(Boolean);
            await updateNote(selectedNote.id, {
                title: editTitle,
                content: editContent,
                tags: tagsArray
            });
            setIsEditing(false);
            toast({ title: 'Note updated successfully' });
        } catch (error) {
            toast({ title: 'Failed to update note', variant: 'destructive' });
        }
    };

    const handleDelete = async () => {
        if (!selectedNote) return;

        const success = await deleteNote(selectedNote.id);
        if (success) {
            toast({ title: 'Note deleted' });
            onClose();
        } else {
            toast({ title: 'Failed to delete note', variant: 'destructive' });
        }
        setDeleteDialogOpen(false);
    };

    if (isLoading || !selectedNote) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="w-6 h-6 border-2 border-[#CE0E2D] border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    // Handle viewing source message
    const handleViewSource = () => {
        if (selectedNote.metadata?.session_id) {
            // Switch session if needed
            // Though we might need to scroll to message which is harder
            switchSession(selectedNote.metadata.session_id);
            toast({ title: "Switched to source session" });
        }
    };

    return (
        <div className="h-full flex flex-col bg-white overflow-hidden">
            {/* Header */}
            <div className="flex-shrink-0 flex items-center justify-between px-6 py-4 border-b border-gray-100">
                <div className="flex items-center gap-2 overflow-hidden">
                    {isEditing ? (
                        <Input
                            value={editTitle}
                            onChange={(e) => setEditTitle(e.target.value)}
                            className="h-8 font-semibold text-lg border-transparent hover:border-gray-200 focus:border-gray-300 px-0"
                            placeholder="Note Title"
                        />
                    ) : (
                        <h2 className="text-xl font-bold text-gray-900 truncate">
                            {selectedNote.title || 'Untitled Note'}
                        </h2>
                    )}
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                    {isEditing ? (
                        <>
                            <Button variant="ghost" size="sm" onClick={() => setIsEditing(false)}>Cancel</Button>
                            <Button size="sm" onClick={handleSave} className="bg-[#CE0E2D] hover:bg-[#A20A22]">
                                <Save className="h-4 w-4 mr-1.5" />
                                Save
                            </Button>
                        </>
                    ) : (
                        <>
                            <Button variant="ghost" size="icon" onClick={() => setIsEditing(true)} title="Edit">
                                <Edit2 className="h-4 w-4 text-gray-500" />
                            </Button>
                            <Button variant="ghost" size="icon" onClick={() => setDeleteDialogOpen(true)} title="Delete">
                                <Trash2 className="h-4 w-4 text-gray-500 hover:text-red-600" />
                            </Button>
                            <div className="w-px h-4 bg-gray-200 mx-1" />
                            <Button variant="ghost" size="icon" onClick={onClose} title="Close">
                                <X className="h-5 w-5 text-gray-400" />
                            </Button>
                        </>
                    )}
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-gray-200">
                <div className="max-w-3xl mx-auto space-y-6">
                    {/* Metadata */}
                    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-gray-500">
                        <div className="flex items-center">
                            <Calendar className="h-4 w-4 mr-1.5" />
                            Created {formatDistanceToNow(new Date(selectedNote.created_at), { addSuffix: true })}
                        </div>

                        {selectedNote.created_from === 'chat' && (
                            <button
                                onClick={handleViewSource}
                                className="flex items-center hover:text-[#CE0E2D] transition-colors"
                                disabled={!selectedNote.metadata?.session_id}
                            >
                                <ExternalLink className="h-4 w-4 mr-1.5" />
                                From Chat Message
                            </button>
                        )}
                    </div>

                    {/* Tags */}
                    <div className="space-y-2">
                        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Tags</label>
                        {isEditing ? (
                            <Input
                                value={editTags}
                                onChange={(e) => setEditTags(e.target.value)}
                                placeholder="Add tags separated by commas..."
                                className="text-sm"
                            />
                        ) : (
                            <div className="flex flex-wrap gap-2">
                                {selectedNote.tags && selectedNote.tags.length > 0 ? (
                                    selectedNote.tags.map((tag, i) => (
                                        <Badge key={i} variant="secondary" className="px-2 py-1 bg-gray-100 text-gray-700 font-medium rounded-md">
                                            <Tag className="h-3 w-3 mr-1.5 opacity-60" />
                                            {tag}
                                        </Badge>
                                    ))
                                ) : (
                                    <span className="text-gray-400 text-sm italic">No tags</span>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Note Body */}
                    <div className="space-y-2">
                        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Content</label>
                        {isEditing ? (
                            <Textarea
                                value={editContent}
                                onChange={(e) => setEditContent(e.target.value)}
                                className="min-h-[400px] font-mono text-sm leading-relaxed"
                                placeholder="Write your note here..."
                            />
                        ) : (
                            <div className="prose prose-sm max-w-none prose-p:text-gray-800 prose-headings:text-gray-900 prose-a:text-[#CE0E2D]">
                                <ReactMarkdown
                                    remarkPlugins={[remarkGfm, remarkMath]}
                                    rehypePlugins={[
                                        rehypeRaw,
                                        [rehypeKatex, { strict: false, throwOnError: false, output: 'html' }],
                                        rehypeHighlight
                                    ]}
                                >
                                    {selectedNote.content}
                                </ReactMarkdown>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <DeleteConfirmationDialog
                isOpen={deleteDialogOpen}
                title="Delete Note"
                message="Are you sure you want to delete this note? This action cannot be undone."
                onConfirm={handleDelete}
                onCancel={() => setDeleteDialogOpen(false)}
            />
        </div>
    );
};

export default NoteViewer;
