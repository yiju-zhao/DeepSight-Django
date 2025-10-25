// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Component focused solely on displaying file content

import React, { useState, useMemo, useEffect } from 'react';
import {
  X,
  Edit,
  Save,
  Download,
  Maximize2,
  Minimize2
} from 'lucide-react';
import { Button } from "@/shared/components/ui/button";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import AuthenticatedImage from './AuthenticatedImage';

interface MarkdownContentProps {
  content: string;
  notebookId: string;
}

// ====== SINGLE RESPONSIBILITY: Markdown content renderer ======
const MarkdownContent = React.memo<MarkdownContentProps>(({ content, notebookId }) => (
  <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-a:text-blue-600 prose-strong:text-gray-900 prose-code:text-red-600 prose-pre:bg-white">
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[
        rehypeHighlight,
        rehypeRaw,
        [rehypeKatex, {
          strict: false,
          throwOnError: false,
          errorColor: '#cc0000',
          trust: true,
          macros: {
            '\\abs': '\\left|#1\\right|',
            '\\pmb': '\\boldsymbol{#1}',
            '\\hdots': '\\cdots',
            '\\RR': '\\mathbb{R}',
            '\\NN': '\\mathbb{N}',
            '\\CC': '\\mathbb{C}',
            '\\ZZ': '\\mathbb{Z}',
          }
        }]
      ]}
      components={{
        img: ({ src, alt, title }) => (
          <AuthenticatedImage src={src || ''} alt={alt} title={title} />
        )
      }}
    >
      {content}
    </ReactMarkdown>
  </div>
));

MarkdownContent.displayName = 'MarkdownContent';

interface FileViewerProps {
  file: any;
  content?: string;
  isExpanded: boolean;
  viewMode: 'preview' | 'edit';
  onClose: () => void;
  onEdit?: () => void;
  onSave: (content: string) => void;
  onDownload?: () => void;
  onToggleExpand: () => void;
  onToggleViewMode?: () => void;
  onContentChange?: (content: string) => void;
  notebookId: string;
  hideHeader?: boolean;
  isPreviewingEdits?: boolean;
}

// ====== INTERFACE SEGREGATION PRINCIPLE (ISP) ======
// Focused props interface for file viewing
const FileViewer: React.FC<FileViewerProps> = ({
  file,
  content,
  isExpanded,
  viewMode, // 'preview' or 'edit'
  onClose,
  onEdit,
  onSave,
  onDownload,
  onToggleExpand,
  onToggleViewMode,
  onContentChange,
  notebookId,
  hideHeader = false,
  isPreviewingEdits = false
}) => {
  const [editContent, setEditContent] = useState(content || '');

  // Update editContent when content prop changes
  useEffect(() => {
    setEditContent(content || '');
  }, [content]);

  // Process the content for display - backend now handles all image URL replacement
  const processedContent = useMemo(() => {
    // If we're in preview mode and previewing edits, use the edit content
    if (viewMode === 'preview' && isPreviewingEdits) {
      return editContent;
    }

    // Otherwise use the content from props (already processed by backend)
    return content;
  }, [content, editContent, isPreviewingEdits, viewMode]);

  const handleSave = () => {
    onSave(editContent);
    onToggleViewMode?.(); // Switch back to preview mode
  };

  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newContent = e.target.value;
    setEditContent(newContent);
    onContentChange?.(newContent);
  };

  const formatFileTitle = () => {
    if (file.title) return file.title;
    if (file.article_title) return file.article_title;
    if (file.name) return file.name;
    return 'Untitled File';
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* ====== SINGLE RESPONSIBILITY: Toolbar rendering ====== */}
      {!hideHeader && (
        <div className="flex-shrink-0 bg-white">
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center space-x-3">
              <h3 className="text-lg font-semibold text-gray-900 truncate">
                {formatFileTitle()}
              </h3>
            </div>

            <div className="flex items-center space-x-2">
              {viewMode === 'preview' && onEdit && (
                <Button variant="outline" size="sm" onClick={onEdit}>
                  <Edit className="h-4 w-4 mr-1" />
                  {isPreviewingEdits ? 'Back to Edit' : 'Edit'}
                </Button>
              )}

              {viewMode === 'edit' && (
                <Button variant="outline" size="sm" onClick={handleSave}>
                  <Save className="h-4 w-4 mr-1" />
                  Save
                </Button>
              )}

              {onDownload && (
                <Button variant="outline" size="sm" onClick={onDownload}>
                  <Download className="h-4 w-4 mr-1" />
                  Download
                </Button>
              )}

              <Button
                variant="outline"
                size="sm"
                onClick={onToggleExpand}
                title={isExpanded ? "Minimize" : "Expand"}
              >
                {isExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={onClose}
                className="text-red-600 border-red-300 hover:bg-red-50"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ====== SINGLE RESPONSIBILITY: Content rendering ====== */}
      <div className="flex-1 overflow-auto">
        {viewMode === 'edit' ? (
          <textarea
            value={editContent}
            onChange={handleContentChange}
            className="w-full h-full p-6 border-none resize-none focus:outline-none font-mono text-sm"
            placeholder="Enter markdown content..."
          />
        ) : (
          <div className="p-6">
            {processedContent ? (
              <MarkdownContent
                content={processedContent || ''}
                notebookId={notebookId}
              />
            ) : (
              <div className="text-center py-12">
                <p className="text-gray-500">No content available</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default React.memo(FileViewer); // Performance optimization
