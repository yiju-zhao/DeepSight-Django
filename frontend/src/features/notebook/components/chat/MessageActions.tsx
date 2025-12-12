import React from 'react';
import { Copy, FileText } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import { useToast } from '@/shared/components/ui/use-toast';
import { useNotes } from '@/features/notebook/hooks/notes/useNotes';

interface MessageActionsProps {
    messageContent: string;
    messageId: string;
    notebookId: string;
}

export const MessageActions: React.FC<MessageActionsProps> = ({
    messageContent,
    messageId,
    notebookId,
}) => {
    const { toast } = useToast();
    const { createNoteFromMessage } = useNotes(notebookId);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(messageContent);
            toast({
                title: 'Copied to clipboard',
                description: 'Message content copied to clipboard',
            });
        } catch (error) {
            toast({
                title: 'Copy failed',
                description: 'Failed to copy to clipboard',
                variant: 'destructive',
            });
        }
    };

    const handleAddToStudio = async () => {
        const numericId = parseInt(messageId, 10);

        if (isNaN(numericId)) {
            toast({
                title: "Cannot save note",
                description: "This message cannot be saved to notes (temporary or invalid ID).",
                variant: "destructive"
            });
            return;
        }

        const result = await createNoteFromMessage({
            message_id: numericId,
        });

        if (result) {
            toast({
                title: 'Note Created',
                description: 'Message saved to Studio notes',
            });
        } else {
            toast({
                title: 'Error',
                description: 'Failed to create note from message',
                variant: 'destructive',
            });
        }
    };

    return (
        <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center space-x-1 bg-white/80 backdrop-blur-sm rounded-md p-1 shadow-sm border border-gray-100">
            <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 hover:bg-gray-100 text-gray-500 hover:text-gray-900"
                onClick={handleCopy}
                title="Copy to clipboard"
            >
                <Copy className="h-3.5 w-3.5" />
            </Button>
            <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 hover:bg-gray-100 text-gray-500 hover:text-[#CE0E2D]"
                onClick={handleAddToStudio}
                title="Add to Studio Notes"
            >
                <FileText className="h-3.5 w-3.5" />
            </Button>
        </div>
    );
};

export default MessageActions;
