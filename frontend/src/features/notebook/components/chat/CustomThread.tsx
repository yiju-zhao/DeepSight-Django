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

// Preprocess text to convert LaTeX delimiters
// Convert [ ... ] to $$ ... $$ (display math)
// Convert ( ... ) to $ ... $ (inline math) if they contain LaTeX
const preprocessLaTeX = (text: string): string => {
  let processed = text;

  // 1. Convert \[ ... \] to $$ ... $$ (display math)
  // Use [\s\S] to match across newlines
  processed = processed.replace(/\\\[([\s\S]*?)\\\]/g, '$$$$$1$$$$');

  // 2. Convert \( ... \) to $ ... $ (inline math)
  processed = processed.replace(/\\\(([\s\S]*?)\\\)/g, '$$$1$$');

  // 3. Convert [ ... ] to $$ ... $$ (display math)
  // Be careful not to match citations like [1] or [ID:0]
  processed = processed.replace(/\[\s*([\s\S]*?)\s*\]/g, (match, content) => {
    // If it looks like a citation (numbers or ID:...), ignore
    if (/^(ID:)?\d+$/.test(content.trim()) || /^\d+(,\s*\d+)*$/.test(content.trim())) {
      return match;
    }
    // Check if it looks like LaTeX (contains backslashes or common math symbols)
    if (content.includes('\\') || /[=\+\-\*\/^∫∑∏∂∇α-ωΑ-Ω]/.test(content)) {
      return `$$$$${content}$$$$`;
    }
    return match;
  });

  return processed;
};


// Memoized markdown content component
const MarkdownContent = React.memo(({ content }: { content: string }) => {
  const processedContent = preprocessLaTeX(content);

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
const CustomMessage: React.FC = () => {
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
                </div>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
};

// Custom Composer Component
const CustomComposer: React.FC = () => {
  const composerRuntime = useComposerRuntime();
  const [inputValue, setInputValue] = React.useState('');
  const [isSending, setIsSending] = React.useState(false);
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex-shrink-0 px-6 py-4 bg-white border-t border-[#F7F7F7]">
      <div className="bg-[#F7F7F7] rounded-[24px] focus-within:ring-1 focus-within:ring-[#E5E5E5] transition-all duration-200">
        <div className="flex items-end space-x-3 px-4 py-3">
          <div className="flex-1 min-h-[24px] flex items-center">
            <Textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => {
                setInputValue(e.target.value);
                composerRuntime.setText(e.target.value);
              }}
              onKeyDown={handleKeyPress}
              placeholder="Type your message..."
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
    </div>
  );
};

// Custom Thread Component
export const CustomThread: React.FC = () => {
  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent">
        <CustomMessage />
      </div>
      <CustomComposer />
    </div>
  );
};

export default CustomThread;
