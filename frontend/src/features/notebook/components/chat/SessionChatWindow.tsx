import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, Loader2, Copy, RotateCcw, Sparkles, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/shared/components/ui/button';
import { Textarea } from '@/shared/components/ui/textarea';
import { Badge } from '@/shared/components/ui/badge';
import { Alert, AlertDescription } from '@/shared/components/ui/alert';
import { useToast } from '@/shared/components/ui/use-toast';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';
import 'highlight.js/styles/github.css';
import type { SessionChatWindowProps } from '@/features/notebook/type';

// Memoized markdown content component
const MarkdownContent = React.memo(({ content }: { content: string }) => (
  <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-strong:text-gray-900 prose-code:text-gray-800 prose-pre:bg-gray-900 prose-pre:text-gray-100">
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight, rehypeRaw]}
      components={{
        h1: ({ children }) => <h1 className="text-lg font-bold text-gray-900 mb-3 pb-2 border-b">{children}</h1>,
        h2: ({ children }) => <h2 className="text-base font-semibold text-gray-800 mt-4 mb-2">{children}</h2>,
        h3: ({ children }) => <h3 className="text-sm font-medium text-gray-800 mt-3 mb-2">{children}</h3>,
        p: ({ children }) => <p className="text-gray-700 leading-relaxed mb-2">{children}</p>,
        ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-1">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-1">{children}</ol>,
        li: ({ children }) => <li className="text-gray-700 text-sm">{children}</li>,
        blockquote: ({ children }) => <blockquote className="border-l-2 border-red-200 pl-3 italic text-gray-600 my-2">{children}</blockquote>,
        code: ({ children }) => <code className="bg-white px-1 py-0.5 rounded text-xs font-mono text-gray-800 border border-gray-200">{children}</code>,
        pre: ({ children }) => <pre className="bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto my-2 text-xs">{children}</pre>,
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-red-600 hover:text-red-800 underline"
          >
            {children}
          </a>
        ),
        table: ({ children }) => <table className="min-w-full border-collapse border border-gray-300 my-2">{children}</table>,
        th: ({ children }) => <th className="border border-gray-300 px-2 py-1 bg-white text-xs font-medium">{children}</th>,
        td: ({ children }) => <td className="border border-gray-300 px-2 py-1 text-xs">{children}</td>,
      }}
    >
      {content}
    </ReactMarkdown>
  </div>
));

MarkdownContent.displayName = 'MarkdownContent';

const SessionChatWindow: React.FC<SessionChatWindowProps> = ({
  session,
  messages,
  isLoading,
  onSendMessage,
  notebookId,
}) => {
  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, [inputMessage]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || !session || isSending) return;

    const messageToSend = inputMessage.trim();
    setInputMessage('');
    setIsSending(true);
    setError(null);

    try {
      const success = await onSendMessage(messageToSend);
      if (!success) {
        // If message failed, restore the input
        setInputMessage(messageToSend);
        setError('Failed to send message. Please try again.');
      }
    } catch (error) {
      setInputMessage(messageToSend);
      const errorMessage = error instanceof Error ? error.message : 'Failed to send message';
      setError(errorMessage);
      toast({
        title: 'Message Failed',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const copyMessage = async (content: string) => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(content);
        toast({
          title: 'Copied',
          description: 'Message copied to clipboard',
        });
      } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = content;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        toast({
          title: 'Copied',
          description: 'Message copied to clipboard',
        });
      }
    } catch (error) {
      toast({
        title: 'Copy Failed',
        description: 'Failed to copy message to clipboard',
        variant: 'destructive',
      });
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (!session) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50">
        <div className="text-center text-gray-500">
          <Bot className="h-12 w-12 mx-auto mb-4 text-gray-400" />
          <p>No session selected</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Error Alert */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex-shrink-0 px-6 py-3 border-b border-gray-200"
          >
            <Alert variant="destructive" className="border-red-200 bg-red-50">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-sm text-red-800">
                {error}
                <Button
                  variant="ghost"
                  size="sm"
                  className="ml-2 h-6 px-2 text-red-600 hover:text-red-800"
                  onClick={() => setError(null)}
                >
                  Dismiss
                </Button>
              </AlertDescription>
            </Alert>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent">
        {messages.length === 0 && !isLoading ? (
          <div className="h-full flex items-center justify-center p-8">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 bg-gradient-to-br from-red-100 to-rose-100 rounded-2xl mx-auto mb-4 flex items-center justify-center">
                <Sparkles className="h-8 w-8 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Ready to Chat</h3>
              <p className="text-gray-600 leading-relaxed">
                This is the beginning of your conversation in "{session.title}". 
                Ask me anything about your knowledge base!
              </p>
            </div>
          </div>
        ) : (
          <div className="p-6 space-y-6">
            <AnimatePresence>
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`flex space-x-3 ${message.sender === 'user' ? 'max-w-[85%] flex-row-reverse space-x-reverse' : 'w-full'}`}>
                    {/* Avatar - only for user messages */}
                    {message.sender === 'user' && (
                      <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-gray-700 text-white">
                        <User className="h-4 w-4" />
                      </div>
                    )}

                    {/* Message Content */}
                    <div className={`group relative ${message.sender === 'user' ? '' : 'w-full'}`}>
                      {message.sender === 'user' ? (
                        <div className="px-4 py-3 rounded-2xl bg-gray-200 text-gray-900 rounded-br-md">
                          <p className="text-sm leading-relaxed">{message.message}</p>
                        </div>
                      ) : (
                        <div className="py-2">
                          <MarkdownContent content={message.message} />
                        </div>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Typing Indicator */}
            {(isLoading || isSending) && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex justify-start"
              >
                <div className="flex space-x-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-red-100 to-rose-100 flex items-center justify-center">
                    <Bot className="h-4 w-4 text-red-600" />
                  </div>
                  <div className="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-3 flex items-center space-x-2 border border-gray-200">
                    <Loader2 className="h-4 w-4 animate-spin text-gray-500" />
                    <span className="text-sm text-gray-600">Thinking...</span>
                  </div>
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="flex-shrink-0 p-6 bg-gray-50/50 border-t border-gray-200">
        <div className="flex items-end space-x-3 bg-white rounded-2xl p-4 shadow-sm border border-gray-200 focus-within:ring-2 focus-within:ring-red-300 focus-within:border-red-300">
          <div className="flex-1 min-h-[40px]">
            <Textarea
              ref={textareaRef}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder={`Message ${session.title}...`}
              className="border-0 resize-none shadow-none focus-visible:ring-0 p-0 max-h-[120px] scrollbar-thin scrollbar-thumb-gray-300"
              disabled={isSending}
            />
          </div>
          <Button
            onClick={handleSendMessage}
            disabled={!inputMessage.trim() || isSending}
            size="sm"
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl shadow-md hover:shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default SessionChatWindow;
