import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, Loader2, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/shared/components/ui/button';
import { Textarea } from '@/shared/components/ui/textarea';
// import { Badge } from '@/shared/components/ui/badge';
import { Alert, AlertDescription } from '@/shared/components/ui/alert';
import { useToast } from '@/shared/components/ui/use-toast';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeHighlight from 'rehype-highlight';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import 'highlight.js/styles/github.css';
import 'katex/dist/katex.min.css';
// import QuestionSuggestions from './QuestionSuggestions';
import type { SessionChatWindowProps } from '@/features/notebook/type';

// Memoized markdown content component
const MarkdownContent = React.memo(({ content }: { content: string }) => (
  <div className="prose prose-base max-w-none prose-headings:font-semibold prose-p:text-gray-800 prose-strong:text-gray-900 prose-code:text-gray-800">
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeKatex, rehypeHighlight, rehypeRaw]}
      components={{
        h1: ({ children }) => <h1 className="text-lg font-semibold text-gray-900 mb-2 mt-4">{children}</h1>,
        h2: ({ children }) => <h2 className="text-base font-semibold text-gray-900 mt-3 mb-1.5">{children}</h2>,
        h3: ({ children }) => <h3 className="text-sm font-semibold text-gray-900 mt-2 mb-1.5">{children}</h3>,
        p: ({ children }) => <p className="text-gray-800 leading-6 mb-2 text-sm">{children}</p>,
        ul: ({ children }) => <ul className="list-disc pl-5 mb-2 space-y-1">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-5 mb-2 space-y-1">{children}</ol>,
        li: ({ children }) => <li className="text-gray-800 text-sm leading-6">{children}</li>,
        blockquote: ({ children }) => <blockquote className="border-l-4 border-gray-300 pl-4 py-2 my-4 italic text-gray-700 bg-white rounded-r">{children}</blockquote>,
        code: ({ children }) => <code className="bg-white px-1.5 py-0.5 rounded text-sm font-mono text-gray-900">{children}</code>,
        pre: ({ children }) => <pre className="bg-gray-950 text-gray-100 p-4 rounded-lg overflow-x-auto my-4 text-sm shadow-sm">{children}</pre>,
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-700 underline decoration-blue-400 hover:decoration-blue-600 transition-colors"
          >
            {children}
          </a>
        ),
        table: ({ children }) => (
          <div className="my-4 overflow-x-auto">
            <table className="min-w-full border-collapse border border-gray-200 rounded-lg overflow-hidden">{children}</table>
          </div>
        ),
        th: ({ children }) => <th className="border border-gray-200 px-4 py-2 bg-white text-sm font-semibold text-left">{children}</th>,
        td: ({ children }) => <td className="border border-gray-200 px-4 py-2 text-sm">{children}</td>,
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
  suggestions,
  isLoading,
  onSendMessage,
  notebookId,
}) => {
  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load suggestions from localStorage on mount
  useEffect(() => {
    if (session && notebookId) {
      const storageKey = `chat_suggestions_${notebookId}_${session.id}`;
      const savedSuggestions = localStorage.getItem(storageKey);
      if (savedSuggestions) {
        try {
          const parsed = JSON.parse(savedSuggestions);
          if (Array.isArray(parsed) && parsed.length > 0) {
            setShowSuggestions(true);
          }
        } catch (error) {
          console.warn('Failed to parse saved suggestions:', error);
        }
      }
    }
  }, [session, notebookId]);

  // Save suggestions to localStorage when they change
  useEffect(() => {
    if (session && notebookId && suggestions && suggestions.length > 0) {
      const storageKey = `chat_suggestions_${notebookId}_${session.id}`;
      localStorage.setItem(storageKey, JSON.stringify(suggestions));
      setShowSuggestions(true);
    }
  }, [suggestions, session, notebookId]);

  // Show suggestions when there are messages and suggestions available
  useEffect(() => {
    if (messages.length > 0 && suggestions && suggestions.length > 0) {
      setShowSuggestions(true);
    }
  }, [messages, suggestions]);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, [inputMessage]);

  const handleSendMessage = async (message? : string) => {
    const messageToSend = message || inputMessage.trim();
    if (!messageToSend || !session || isSending) return;

    setInputMessage('');
    setIsSending(true);
    setError(null);
    setShowSuggestions(false);

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
      <div className="h-full flex items-center justify-center bg-white">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-white border-2 border-gray-200 rounded-2xl mb-4">
            <Bot className="h-10 w-10 text-gray-400" strokeWidth={1.5} />
          </div>
          <p className="text-sm text-gray-500 font-medium">No session selected</p>
          <p className="text-xs text-gray-400 mt-2">Select a chat session to continue</p>
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
            className="flex-shrink-0 px-6 py-3 bg-white"
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
            <div className="text-center max-w-lg">
              
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.3 }}
                className="inline-flex items-center space-x-2 px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-xs text-gray-600"
              >
                <Bot className="h-4 w-4" />
                <span>Ask me anything about your knowledge base</span>
              </motion.div>
            </div>
          </div>
        ) : (
          <div className="p-8 space-y-5 max-w-4xl mx-auto">
            <AnimatePresence>
              {messages.map((message) => {
                return (
                  <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`flex space-x-4 ${message.sender === 'user' ? 'max-w-[80%] flex-row-reverse space-x-reverse' : 'w-full'}`}>
                      {/* Avatar */}
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                        message.sender === 'user'
                          ? 'bg-gradient-to-br from-gray-700 to-gray-800 text-white'
                          : 'bg-white border-2 border-gray-200 text-gray-600'
                      }`}>
                        {message.sender === 'user' ? (
                          <User className="h-4 w-4" />
                        ) : (
                          <Bot className="h-4 w-4" />
                        )}
                      </div>

                      {/* Message Content */}
                      <div className={`group relative ${message.sender === 'user' ? '' : 'w-full'}`}>
                        {message.sender === 'user' ? (
                          <div className="px-4 py-2.5 rounded-2xl bg-white text-gray-900">
                            <p className="text-sm leading-6">{message.message}</p>
                          </div>
                        ) : (
                          <div className="px-4 py-3 rounded-2xl bg-white">
                            <MarkdownContent content={message.message} />
                          </div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="flex-shrink-0 p-6 bg-white">
        <div className="bg-white rounded-2xl shadow-sm focus-within:ring-2 focus-within:ring-red-300">
          {/* Suggestions as tags inside input area */}
          {showSuggestions && suggestions && suggestions.length > 0 && (
            <div className="px-4 pt-3 pb-2">
              <div className="flex flex-wrap gap-2">
                {(suggestions.slice(0, 3)).map((sugg, i) => (
                  <Button
                    key={`${i}-${sugg}`}
                    variant="outline"
                    size="sm"
                    onClick={() => handleSendMessage(sugg)}
                    className="h-6 rounded-full px-2 py-1 text-xs bg-gray-50 border-gray-200 hover:bg-gray-100 text-gray-700"
                  >
                    {sugg}
                  </Button>
                ))}
              </div>
            </div>
          )}

          <div className="flex items-end space-x-3 p-4">
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
              onClick={() => handleSendMessage()}
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
    </div>
  );
};

export default SessionChatWindow;
