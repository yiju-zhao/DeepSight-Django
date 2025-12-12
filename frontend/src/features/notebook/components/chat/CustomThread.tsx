/**
 * Custom Thread component for DeepSight
 * Matches the original design with markdown rendering and custom styling
 */

import React from 'react';
import { User, Bot, Send, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeHighlight from 'rehype-highlight';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import {
  useThread,
  useComposerRuntime,
} from '@assistant-ui/react';
import { Button } from '@/shared/components/ui/button';
import { Textarea } from '@/shared/components/ui/textarea';
import 'highlight.js/styles/github.css';
import 'katex/dist/katex.min.css';

// Import Studio Mode components
import StudioModeToggle from './StudioModeToggle';
import MessageActions from './MessageActions';
import { useNotebookSettings } from '@/features/notebook/contexts/NotebookSettingsContext';

// Normalizer to convert backend-specific LaTeX formats to standard Markdown LaTeX
// This follows a "First Principles" approach by respecting Markdown structure (code blocks)
// before applying text transformations.
const normalizeMarkdown = (text: string): string => {
  // 1. Split text by code blocks to protect them from processing
  // Capturing group (...) keeps the separators in the result array
  const parts = text.split(/(```[\s\S]*?```|`[^`\n]+`)/g);

  return parts.map((part) => {
    // Check if this part is a code block (starts with `)
    if (part.startsWith('`')) {
      return part;
    }

    // Process non-code text
    let processed = part;

    // 1. Convert \[ ... \] to $$ ... $$ (display math)
    processed = processed.replace(/\\\[([\s\S]*?)\\\]/g, (match, content) => `$$${content}$$`);

    // 2. Convert \( ... \) to $ ... $ (inline math)
    processed = processed.replace(/\\\(([\s\S]*?)\\\)/g, (match, content) => `$${content}$`);

    // 3. Convert standalone [ ... ] to $$ ... $$ (display math)
    // Only match when [ is at the start of a line (ignoring whitespace)
    // and ] is at the end of a line
    processed = processed.replace(/^\s*\[\s*([\s\S]*?)\s*\]\s*$/gm, (match, content) => {
      // Skip if it looks like a citation: [ID:x] or [number]
      const trimmed = content.trim();
      if (/^ID:\d+$/.test(trimmed) || /^\d+$/.test(trimmed)) {
        return match;
      }
      // Convert to display math
      return `$$${content}$$`;
    });

    return processed;
  }).join('');
};


// Memoized markdown content component
const MarkdownContent = React.memo(({ content }: { content: string }) => {
  const processedContent = normalizeMarkdown(content);

  return (
    <div className="prose prose-base max-w-none prose-headings:font-semibold prose-p:text-gray-800 prose-strong:text-gray-900 prose-code:text-gray-800">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[
          rehypeRaw,
          [rehypeKatex, { strict: false, throwOnError: false, output: 'html' }],
          rehypeHighlight
        ]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-lg font-semibold text-gray-900 mb-2 mt-4">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-base font-semibold text-gray-900 mt-3 mb-1.5">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-sm font-semibold text-gray-900 mt-2 mb-1.5">
              {children}
            </h3>
          ),
          p: ({ children }) => (
            <p className="text-gray-800 leading-6 mb-2 text-sm">{children}</p>
          ),
          ul: ({ children }) => (
            <ul className="list-disc pl-5 mb-2 space-y-1">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal pl-5 mb-2 space-y-1">{children}</ol>
          ),
          li: ({ children }) => (
            <li className="text-gray-800 text-sm leading-6">{children}</li>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-gray-200 pl-4 py-2 my-4 italic text-gray-700 rounded-r">
              {children}
            </blockquote>
          ),
          code: ({ inline, className, children, ...props }: any) => {
            // Don't style math-related code elements
            if (className?.includes('language-math')) {
              return <code {...props}>{children}</code>;
            }
            return inline ? (
              <code className="bg-white px-1.5 py-0.5 rounded text-sm font-mono text-gray-900">
                {children}
              </code>
            ) : (
              <code {...props}>{children}</code>
            );
          },
          pre: ({ children }) => (
            <pre className="bg-gray-950 text-gray-100 p-4 rounded-lg overflow-x-auto my-4 text-sm shadow-sm">
              {children}
            </pre>
          ),
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
              <table className="min-w-full border-collapse rounded-lg overflow-hidden">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="px-4 py-2 bg-gray-50 text-sm font-semibold text-left">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-4 py-2 text-sm border-b border-gray-100">
              {children}
            </td>
          ),
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
});

MarkdownContent.displayName = 'MarkdownContent';

// Custom Message Component
const CustomMessage: React.FC<{ notebookId: string }> = ({ notebookId }) => {
  const thread = useThread();
  const messages = thread.messages;


  return (
    <div className="px-6 py-6 space-y-5 max-w-3xl mx-auto">
      <AnimatePresence>
        {messages.map((message) => {
          const isUser = message.role === 'user';
          const textContent = message.content.find(
            (part) => part.type === 'text'
          );
          const text = textContent?.type === 'text' ? textContent.text : '';

          return (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`flex space-x-4 ${isUser
                  ? 'max-w-[80%] flex-row-reverse space-x-reverse'
                  : 'w-full'
                  }`}
              >
                {/* Avatar */}
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${isUser
                    ? 'bg-[#1E1E1E] text-white'
                    : 'bg-[#CE0E2D] text-white'
                    }`}
                >
                  {isUser ? (
                    <User className="h-4 w-4" />
                  ) : (
                    <Bot className="h-4 w-4" />
                  )}
                </div>

                {/* Message Content */}
                <div className={`group relative ${isUser ? '' : 'w-full'}`}>
                  {isUser ? (
                    <div className="px-5 py-3 rounded-2xl bg-[#F5F5F5] text-[#1E1E1E]">
                      <p className="text-[14px] leading-[1.6]">{text}</p>
                    </div>
                  ) : (
                    <div className="px-6 py-4 rounded-2xl bg-white shadow-[0_2px_8px_rgba(0,0,0,0.04)] border border-[#F7F7F7]">
                      <MarkdownContent content={text} />
                    </div>
                  )}
                  {!isUser && (
                    <MessageActions
                      messageContent={text}
                      messageId={message.id}
                      notebookId={notebookId}
                    />
                  )}
                </div>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
};

// Custom Composer Component with Studio Mode Toggle
interface CustomComposerProps {
  suggestions?: string[];
  onSuggestionClick?: (suggestion: string) => void;
}

const CustomComposer: React.FC<CustomComposerProps> = ({ suggestions, onSuggestionClick }) => {
  const composerRuntime = useComposerRuntime();
  const [inputValue, setInputValue] = React.useState('');
  const [isSending, setIsSending] = React.useState(false);
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  // Get studio mode state from context
  const { studioMode, toggleStudioMode } = useNotebookSettings();

  // Auto-resize textarea
  React.useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, [inputValue]);

  const handleSend = async () => {
    if (!inputValue.trim() || isSending) return;

    setIsSending(true);
    try {
      await composerRuntime.send();
      setInputValue('');
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsSending(false);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion);
    composerRuntime.setText(suggestion);
    if (onSuggestionClick) {
      onSuggestionClick(suggestion);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex-shrink-0 px-6 py-4 bg-white border-t border-[#F7F7F7]">
      {/* Suggestions Area */}
      {suggestions && suggestions.length > 0 && !studioMode && (
        <div className="flex w-full gap-2 mb-3">
          {suggestions.slice(0, 3).map((sugg, i) => (
            <button
              key={`${i}-${sugg}`}
              onClick={() => handleSuggestionClick(sugg)}
              className="flex-1 h-8 px-3 rounded-full bg-gray-50 hover:bg-gray-100 border border-gray-100 text-xs text-gray-600 font-medium transition-colors text-left overflow-hidden whitespace-nowrap text-ellipsis flex items-center"
              title={sugg} // Show full text on hover
            >
              <span className="truncate w-full">{sugg}</span>
            </button>
          ))}
        </div>
      )}

      <div className="bg-[#F7F7F7] rounded-[24px] focus-within:ring-1 focus-within:ring-[#E5E5E5] transition-all duration-200">
        <div className="flex items-end space-x-3 px-4 py-3">
          {/* Studio Mode Toggle - bottom left (like ChatGPT search) */}
          <StudioModeToggle
            isActive={studioMode}
            onToggle={toggleStudioMode}
            disabled={isSending}
          />

          <div className="flex-1 min-h-[24px] flex items-center">
            <Textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => {
                setInputValue(e.target.value);
                composerRuntime.setText(e.target.value);
              }}
              onKeyDown={handleKeyPress}
              placeholder={studioMode
                ? "Describe your research goal... (Studio Mode)"
                : "Type your message..."
              }
              className="border-0 resize-none shadow-none focus-visible:ring-0 p-0 max-h-[120px] min-h-[24px] scrollbar-thin scrollbar-thumb-gray-300 bg-transparent text-[14px] placeholder:text-[#999999]"
              disabled={isSending}
            />
          </div>
          <Button
            onClick={handleSend}
            disabled={!inputValue.trim() || isSending}
            size="sm"
            className="h-8 w-8 p-0 rounded-full bg-[#CE0E2D] hover:bg-[#A20A22] text-white shadow-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center flex-shrink-0 mb-0.5"
          >
            {isSending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4 ml-0.5" />
            )}
          </Button>
        </div>
      </div>

      {/* Studio Mode indicator */}
      {studioMode && (
        <div className="mt-2 px-1 text-[11px] text-[#CE0E2D] flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-[#CE0E2D] animate-pulse" />
          Studio Mode: Messages will use AI agents for research & reports
        </div>
      )}
    </div>
  );
};

// Custom Thread Component
interface CustomThreadProps {
  suggestions?: string[];
  notebookId: string;
}

export const CustomThread: React.FC<CustomThreadProps> = ({ suggestions, notebookId }) => {
  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent">
        <CustomMessage notebookId={notebookId} />
      </div>
      <CustomComposer suggestions={suggestions} />
    </div>
  );
};

export default CustomThread;

