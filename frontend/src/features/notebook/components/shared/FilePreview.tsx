import React, { useState, useEffect, useRef } from 'react';
import { X, Eye, FileText, Globe, Music, Video, File, HardDrive, Calendar, ExternalLink, Loader2, AlertCircle, RefreshCw, Trash2, Plus, ChevronLeft, CheckCircle, Clock, Upload, Link2, Youtube, Group, Presentation, FileSpreadsheet, Copy } from 'lucide-react';
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { supportsPreview, PREVIEW_TYPES, formatDate, getVideoMimeType, getAudioMimeType, generateTextPreviewWithMinIOUrls } from "@/features/notebook/utils/filePreview";
import { createSecureBlob, downloadFileSecurely, createBlobManager } from "@/features/notebook/utils/storageUtils";
import { useFilePreview } from "@/features/notebook/queries";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeHighlight from "rehype-highlight";
import rehypeRaw from "rehype-raw";
import rehypeKatex from "rehype-katex";
import "highlight.js/styles/github.css";
import "katex/dist/katex.min.css";
import "../../styles/math.css";
import GallerySection from "@/features/notebook/components/shared/GallerySection";
import { Source, PreviewState, FileSource } from '@/shared/types';

// API Base URL for raw file access
import { config } from "@/config";

const API_BASE_URL = config.API_BASE_URL;

// Math rendering is handled by KaTeX via rehype-katex plugin - no manual setup needed


// Authenticated Image component for handling images with credentials
interface AuthenticatedImageProps {
  src: string;
  alt?: string;
  title?: string;
  notebookId?: string;
  fileId?: string;
}

// Simple in-memory cache for image lists per file
const imageListCache: Record<string, any[]> = {};

const AuthenticatedImage: React.FC<AuthenticatedImageProps> = ({ src, alt, title, notebookId, fileId }) => {
  const [imgSrc, setImgSrc] = useState(src);
  const [imgError, setImgError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const createdBlobUrlRef = useRef<string | null>(null);

  useEffect(() => {
    // If the src is a blob URL or already a data URL, use it directly
    if (src.startsWith('blob:') || src.startsWith('data:')) {
      setImgSrc(src);
      setIsLoading(false);
      return;
    }

    // Helper to fetch an API inline URL with credentials and convert to blob URL
    const fetchInlineBlob = async (inlineUrl: string) => {
      try {
        const absoluteUrl = inlineUrl.startsWith('/api/') ? `${window.location.origin}${inlineUrl}` : inlineUrl;
        const res = await fetch(absoluteUrl, { credentials: 'include' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const blob = await res.blob();
        const result = createSecureBlob([blob]);
        if (createdBlobUrlRef.current) {
          URL.revokeObjectURL(createdBlobUrlRef.current);
        }
        createdBlobUrlRef.current = result.url;
        setImgSrc(result.url);
        setIsLoading(false);
      } catch (e) {
        console.warn('Failed to fetch inline blob:', e);
        setImgError(true);
        setIsLoading(false);
      }
    };

    // Check if it's a MinIO URL (pre-signed URLs with X-Amz-Signature or minio host)
    const isMinIOUrl = src.includes('X-Amz-Signature') ||
      src.includes('X-Amz-Algorithm') ||
      (src.includes('minio') && src.includes(':9000')) ||
      (src.includes('localhost:9000'));

    if (isMinIOUrl) {
      // Best practice: convert to API inline image and fetch via backend
      (async () => {
        try {
          if (!notebookId || !fileId) throw new Error('Missing notebookId/fileId to resolve image');
          const cacheKey = `${notebookId}:${fileId}`;
          let images: any[] = imageListCache[cacheKey] || [];
          if (images.length === 0) {
            const listUrl = `${API_BASE_URL}/notebooks/${notebookId}/files/${fileId}/images/`;
            const listRes = await fetch(listUrl, { credentials: 'include', headers: { 'Accept': 'application/json' } });
            if (!listRes.ok) throw new Error(`Failed to list images: ${listRes.status}`);
            const listJson = await listRes.json();
            images = listJson.images || [];
            imageListCache[cacheKey] = images;
          }
          const failingName = (src.split('?')[0]?.split('/').pop() || '').toLowerCase();
          if (images) {
            const matched = images.find((im: any) => (im.image_url && im.image_url.toLowerCase().includes(failingName)) || (im.original_filename && String(im.original_filename).toLowerCase().includes(failingName))) || images[0];
            if (!matched || !matched.id) throw new Error('Unable to resolve image to inline API');
            const apiUrl = `${API_BASE_URL}/notebooks/${notebookId}/files/${fileId}/image/${matched.id}/inline/`;
            await fetchInlineBlob(apiUrl);
          }
        } catch (e) {
          console.warn('Failed to convert MinIO URL to API inline:', e);
          setImgError(true);
          setIsLoading(false);
        }
      })();
      return;
    }

    // If it's our API inline endpoint, fetch with credentials and convert to blob URL
    const isApiInline = src.startsWith(`${API_BASE_URL}/notebooks/`) && src.includes('/image/') && src.endsWith('/inline/');
    const isRelativeApiInline = src.startsWith('/api/v1/notebooks/') && src.includes('/image/') && src.endsWith('/inline/');
    if (isApiInline || isRelativeApiInline) {
      const apiUrl = isRelativeApiInline ? `${window.location.origin}${src}` : src;
      fetchInlineBlob(apiUrl);
      return;
    }

    // If it's an API URL to an images endpoint that returns JSON, resolve to actual image URL
    if ((src.includes('/api/v1/notebooks/') && src.includes('/images/')) || (!src.startsWith('http') && notebookId && fileId)) {
      // Try to resolve the image by listing images for this KB item
      const fetchImageWithCredentials = async () => {
        try {
          const cacheKey = `${notebookId}:${fileId}`;
          let images: any[] = imageListCache[cacheKey] || [];
          if (images.length === 0) {
            const listUrl = `${API_BASE_URL}/notebooks/${notebookId}/files/${fileId}/images/`;
            const listRes = await fetch(listUrl, { credentials: 'include', headers: { 'Accept': 'application/json' } });
            if (!listRes.ok) throw new Error(`Failed to list images: ${listRes.status}`);
            const listJson = await listRes.json();
            images = listJson.images || [];
            imageListCache[cacheKey] = images;
          }

          // Extract filename from src
          const srcName = src.split('/').pop() || src;
          if (images) {
            const match = images.find((img: any) =>
              (img.original_filename && img.original_filename.includes(srcName)) ||
              (img.image_url && img.image_url.includes(srcName)) ||
              (img.imageUrl && img.imageUrl.includes(srcName))
            ) || images.find((img: any) => img.image_url);

            if (match && (match.image_url || match.imageUrl)) {
              const resolved = match.image_url || match.imageUrl;
              setImgSrc(resolved);
              setIsLoading(false);
              return;
            }
          }

          // If not found, fall back to original src
          setImgSrc(src);
          setIsLoading(false);
        } catch (error) {
          console.error('Failed to fetch image with credentials:', error);
          setImgError(true);
          setIsLoading(false);
        }
      };

      fetchImageWithCredentials();
    } else {
      // For external URLs, use directly
      setImgSrc(src);
      setIsLoading(false);
    }
  }, [src, notebookId, fileId]);

  // Cleanup blob URL on unmount
  useEffect(() => {
    return () => {
      if (createdBlobUrlRef.current) {
        URL.revokeObjectURL(createdBlobUrlRef.current);
        createdBlobUrlRef.current = null;
      }
    };
  }, []);

  return (
    <span className="my-4 inline-block w-full">
      {isLoading && (
        <span className="bg-[#F5F5F5] border border-[#E3E3E3] rounded-lg p-4 text-center text-[#666666] block">
          <span className="inline-flex items-center justify-center space-x-2">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span className="text-[14px]">Loading image...</span>
          </span>
        </span>
      )}

      {!isLoading && !imgError && (
        <img
          src={imgSrc}
          alt={alt || 'Image'}
          title={title}
          className="max-w-full h-auto rounded-lg border border-[#E3E3E3] shadow-sm"
          style={{ maxHeight: '500px' }}
          onError={(e) => {
            console.error('Image failed to load:', { src: imgSrc, alt, title });
            setImgError(true);
          }}
          onLoad={(e) => {
            console.log('Image loaded successfully:', { src: imgSrc, alt });
          }}
        />
      )}

      {!isLoading && imgError && (
        <span className="bg-[#F5F5F5] border border-[#E3E3E3] rounded-lg p-4 text-center text-[#666666] block">
          <span className="inline-flex items-center justify-center space-x-2">
            <File className="h-5 w-5" />
            <span className="text-[14px]">Image could not be loaded</span>
          </span>
          {alt && <span className="text-[12px] mt-1 text-[#7B7B7B] block">{alt}</span>}
          <span className="text-[12px] mt-1 text-[#7B7B7B] break-all block">URL: {src}</span>
        </span>
      )}
    </span>
  );
};



// Memoized markdown content component (same as StudioPanel)
interface MarkdownContentProps {
  content: string;
  notebookId?: string;
  fileId?: string;
}


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

const MarkdownContent = React.memo<MarkdownContentProps>(({ content, notebookId, fileId }) => {
  // Normalize markdown content first
  const normalizedContent = React.useMemo(() => normalizeMarkdown(content), [content]);

  // Remove non-standard HTML tags (think, result, results, answer, information) that cause React warnings
  const sanitizedContent = React.useMemo(() => {
    return normalizedContent
      // Remove <think> tags
      .replace(/<think>/gi, '')
      .replace(/<\/think>/gi, '')
      .replace(/<think\s*\/>/gi, '')
      // Remove <result> tags
      .replace(/<result>/gi, '')
      .replace(/<\/result>/gi, '')
      .replace(/<result\s*\/>/gi, '')
      // Remove <results> tags
      .replace(/<results>/gi, '')
      .replace(/<\/results>/gi, '')
      .replace(/<results\s*\/>/gi, '')
      // Remove <answer> tags
      .replace(/<answer>/gi, '')
      .replace(/<\/answer>/gi, '')
      .replace(/<answer\s*\/>/gi, '')
      // Remove <information> tags
      .replace(/<information>/gi, '')
      .replace(/<\/information>/gi, '')
      .replace(/<information\s*\/>/gi, '');
  }, [content]);

  return (
    <div className="prose prose-sm max-w-none prose-headings:text-[#1E1E1E] prose-p:text-[#1E1E1E] prose-strong:text-[#1E1E1E] prose-a:text-[#2788D9] prose-code:text-[#CE0E2D] prose-pre:bg-[#24272A]">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[
          rehypeHighlight,
          rehypeRaw,
          [rehypeKatex, {
            strict: false,
            throwOnError: false,
            errorColor: '#CE0E2D',
            trust: true,
            macros: {
              '\\abs': '\\left|#1\\right|',
              '\\pmb': '\\boldsymbol{#1}',
              '\\hdots': '\\cdots',
              '\\RR': '\\mathbb{R}',
              '\\NN': '\\mathbb{N}',
              '\\CC': '\\mathbb{C}',
              '\\ZZ': '\\mathbb{Z}',
              '\\QQ': '\\mathbb{Q}',
            }
          }]
        ]}
        components={{
          h1: ({ children }) => <h1 className="text-[28px] font-bold text-[#1E1E1E] mb-6 pb-3 border-b border-[#E3E3E3]">{children}</h1>,
          h2: ({ children }) => <h2 className="text-[24px] font-bold text-[#1E1E1E] mt-8 mb-4">{children}</h2>,
          h3: ({ children }) => <h3 className="text-[20px] font-semibold text-[#1E1E1E] mt-6 mb-3">{children}</h3>,
          p: ({ children }) => <p className="text-[16px] text-[#1E1E1E] leading-[1.6] mb-4">{children}</p>,
          ul: ({ children }) => <ul className="list-disc pl-6 mb-4 space-y-2 text-[#1E1E1E]">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-6 mb-4 space-y-2 text-[#1E1E1E]">{children}</ol>,
          li: ({ children }) => <li className="text-[#1E1E1E]">{children}</li>,
          blockquote: ({ children }) => <blockquote className="border-l-4 border-[#E3E3E3] pl-4 italic text-[#666666] my-4">{children}</blockquote>,
          code: ({ children }) => <code className="bg-[#F5F5F5] px-1 py-0.5 rounded text-[14px] font-mono text-[#1E1E1E]">{children}</code>,
          pre: ({ children }) => <pre className="bg-[#24272A] text-[#F5F5F5] p-4 rounded-lg overflow-x-auto my-4">{children}</pre>,
          img: ({ src, alt, title, ...props }) => {
            if (!src) return null;
            return <AuthenticatedImage src={src} alt={alt} title={title} notebookId={notebookId} fileId={fileId} />;
          },
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#2788D9] hover:underline break-all"
            >
              {children}
            </a>
          ),
        }}
      >
        {sanitizedContent}
      </ReactMarkdown>
    </div>
  );
});

MarkdownContent.displayName = 'MarkdownContent';

interface FilePreviewState {
  audioError: boolean;
  audioLoaded: boolean;
  videoError: boolean;
  videoLoaded: boolean;
  modals: {
    [key: string]: React.ReactNode;
  };
  resolvedContent?: string | null;
  copyStatus: 'idle' | 'copying' | 'copied';
  hasGalleryImages: boolean;
}

interface FilePreviewComponentProps {
  source: Source;
  isOpen: boolean;
  onClose: () => void;
  notebookId: string;
  useMinIOUrls?: boolean;
}

const FilePreview: React.FC<FilePreviewComponentProps> = ({ source, isOpen, onClose, notebookId, useMinIOUrls = false }) => {
  // Use TanStack Query for data fetching with automatic deduplication and caching
  const {
    data: preview,
    isLoading,
    error,
    refetch
  } = useFilePreview(
    source,
    notebookId,
    useMinIOUrls,
    isOpen && !!source && !!source.metadata?.file_extension && supportsPreview(source.metadata.file_extension || '', source.metadata || {})
  );

  // Simplified state for UI-only concerns
  const [state, setState] = useState<FilePreviewState>({
    audioError: false,
    audioLoaded: false,
    videoError: false,
    videoLoaded: false,
    modals: {},
    resolvedContent: null,
    copyStatus: 'idle',
    hasGalleryImages: false
  });

  // Create blob manager for automatic cleanup
  const blobManager = React.useMemo(() => createBlobManager(), []);

  // Helper function to update state
  const updateState = (updates: Partial<FilePreviewState>) => {
    setState(prevState => ({ ...prevState, ...updates }));
  };

  // Modal handlers
  const openModal = (modalType: string, content: React.ReactNode) => {
    updateState({
      modals: { ...state.modals, [modalType]: content }
    });
  };

  const closeModal = (modalType: string) => {
    const newModals = { ...state.modals };
    delete newModals[modalType];
    updateState({ modals: newModals });
  };

  // Helper function to get file URL (renamed from getRawFileUrl, now uses inline for preview)
  const getFileUrl = (fileId: string, action: 'inline' | 'raw' = 'inline') => {
    return notebookId ?
      `${API_BASE_URL}/notebooks/${notebookId}/files/${fileId}/${action}/` :
      `${API_BASE_URL}/files/${fileId}/${action}/`;
  };

  // Cleanup function to revoke blob URLs when component unmounts or closes
  useEffect(() => {
    if (!isOpen) {
      blobManager.cleanup();
    }
    return () => {
      blobManager.cleanup();
    };
  }, [isOpen, blobManager]);

  // Resolve markdown image paths like images/xxx.jpg to presigned URLs
  useEffect(() => {
    const resolveImagesInContent = async () => {
      try {
        if (!preview?.content || !notebookId || !source?.file_id) return;
        const content = preview.content as string;
        // Quick check: only run if relative images likely present
        if (!content.includes('images/')) {
          updateState({ resolvedContent: null });
          return;
        }

        const cacheKey = `${notebookId}:${source.file_id}`;
        let images: any[] = imageListCache[cacheKey] || [];
        if (images.length === 0) {
          const listUrl = `${API_BASE_URL}/notebooks/${notebookId}/files/${source.file_id}/images/`;
          const listRes = await fetch(listUrl, { credentials: 'include', headers: { 'Accept': 'application/json' } });
          if (!listRes.ok) throw new Error(`Failed to list images: ${listRes.status}`);
          const listJson = await listRes.json();
          images = listJson.images || [];
          imageListCache[cacheKey] = images;
        }

        if (!images || images.length === 0) {
          updateState({ resolvedContent: null });
          return;
        }

        // Build a lookup by basename
        const byName: Record<string, string> = {};
        images.forEach((img: any) => {
          const url = img.image_url || img.imageUrl;
          const orig = img.original_filename || '';
          const base = orig.split('/').pop();
          if (base && url) byName[base] = url;
        });

        let replaced = content;
        // Replace markdown image links ![alt](images/filename)
        replaced = replaced.replace(/!\[[^\\]*\]\((?:\.?\/)?images\/(.+?)\)/g, (m, p1) => {
          const name = String(p1).split(/[?#]/)[0]?.split('/').pop() || String(p1);
          const url = byName[name];
          return url ? m.replace(/\((?:\.?\/)?images\/(.+?)\)/, `(${url})`) : m;
        });

        // Replace HTML <img src="images/filename">
        replaced = replaced.replace(/<img([^>]*?)src=["'](?:\.?\/)?images\/(.+?)["']([^>]*?)>/g, (m, pre, p1, post) => {
          const name = String(p1).split(/[?#]/)[0]?.split('/').pop() || String(p1);
          const url = byName[name];
          return url ? m.replace(/src=["'][^"']+["']/, `src="${url}"`) : m;
        });

        updateState({ resolvedContent: replaced });
      } catch (e) {
        console.warn('Failed to resolve images in content:', e);
        updateState({ resolvedContent: null });
      }
    };

    resolveImagesInContent();
  }, [preview?.content, notebookId, source?.file_id]);


  // Build copyable markdown text based on current preview and resolved content
  const getCopyableMarkdown = React.useCallback((): string | null => {
    if (!preview) return null;
    const fileId = source.file_id || '';
    const nid = notebookId;

    switch (preview.type) {
      case PREVIEW_TYPES.TEXT_CONTENT: {
        const base = (state.resolvedContent ?? preview.content) as string | undefined;
        return base && base.trim().length > 0 ? base : null;
      }
      case PREVIEW_TYPES.AUDIO_INFO:
      case PREVIEW_TYPES.VIDEO_INFO: {
        if ((preview as any).hasTranscript && preview.content) {
          const content = preview.content as string;
          return content && content.trim().length > 0 ? content : null;
        }
        return null;
      }
      default:
        return null;
    }
  }, [preview, state.resolvedContent, notebookId, source?.file_id, useMinIOUrls]);

  const canCopy = React.useMemo(() => {
    const t = getCopyableMarkdown();
    return !!t && t.trim().length > 0;
  }, [getCopyableMarkdown]);

  // Detect if source is a URL type
  const isUrlSource = React.useMemo(() => {
    return source.ext === 'url' ||
      !!source.metadata?.source_url ||
      source.metadata?.extraction_type === 'url_extractor' ||
      source.metadata?.processing_method === 'media' ||
      source.metadata?.processing_method === 'web_scraping_no_crawl4ai' ||
      source.metadata?.processing_method === 'crawl4ai_only';
  }, [source]);

  // Resolve the URL to open
  const openDocumentUrl = React.useMemo(() => {
    if (isUrlSource) {
      // Priority: source_url > url property
      return source.metadata?.source_url || source.url || null;
    } else if (source.file_id) {
      // File source: construct MinIO inline URL
      return `${API_BASE_URL}/notebooks/${notebookId}/files/${source.file_id}/inline/`;
    }
    return null;
  }, [isUrlSource, source, notebookId]);

  // Determine if button should be shown
  const shouldShowOpenDocument = React.useMemo(() => {
    return !!openDocumentUrl && openDocumentUrl.trim().length > 0;
  }, [openDocumentUrl]);

  // Handler function
  const handleOpenDocument = () => {
    if (openDocumentUrl) {
      window.open(openDocumentUrl, '_blank', 'noopener,noreferrer');
    }
  };

  const handleCopyAsMarkdown = async () => {
    try {
      const text = getCopyableMarkdown();
      if (!text) return;
      updateState({ copyStatus: 'copying' });
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      updateState({ copyStatus: 'copied' });
      setTimeout(() => updateState({ copyStatus: 'idle' }), 2000);
    } catch (e) {
      console.error('Copy failed:', e);
      updateState({ copyStatus: 'idle' });
    }
  };

  const getPreviewIcon = (type: string) => {
    switch (type) {
      case PREVIEW_TYPES.TEXT_CONTENT:
        // Check if this is a presentation or spreadsheet file
        const fileExt = source?.metadata?.file_extension?.toLowerCase() || '';
        if (['.ppt', '.pptx'].includes(fileExt)) {
          return Presentation;
        }
        if (['.xlsx', '.xls'].includes(fileExt)) {
          return FileSpreadsheet;
        }
        return FileText;
      case PREVIEW_TYPES.URL_INFO:
        return Globe;
      case PREVIEW_TYPES.AUDIO_INFO:
        return Music;
      case PREVIEW_TYPES.VIDEO_INFO:
        return Video;
      default:
        return File;
    }
  };

  const renderPreviewContent = () => {
    if (isLoading) {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin text-[#666666] mx-auto mb-4" />
            <p className="text-[#666666] text-[14px]">Loading preview...</p>
          </div>
        </div>
      );
    }

    if (error) {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <File className="h-12 w-12 text-[#B1B1B1] mx-auto mb-4" />
            <p className="text-[#CE0E2D] mb-2 font-medium">Preview Error</p>
            <p className="text-[#666666] text-[14px] mb-4">{error?.message || 'Unknown error'}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              className="h-[32px] px-[16px] text-[13px] font-medium border-[#E3E3E3] text-[#1E1E1E] hover:bg-[#F5F5F5]"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </div>
      );
    }

    if (!preview) {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Eye className="h-12 w-12 text-[#B1B1B1] mx-auto mb-4" />
            <p className="text-[#666666] text-[14px]">No preview available</p>
          </div>
        </div>
      );
    }

    switch (preview.type) {
      case PREVIEW_TYPES.TEXT_CONTENT:
        // Check file type for specialized rendering
        if (preview.isPdfPreview) {
          return renderPdfContentPreview();
        }
        // Check if this is an Excel file
        const fileExt = source?.metadata?.file_extension?.toLowerCase() || '';
        if (['.xlsx', '.xls'].includes(fileExt)) {
          return renderExcelContentPreview();
        }
        return renderTextPreview();
      case PREVIEW_TYPES.URL_INFO:
        return renderUrlPreview();
      case PREVIEW_TYPES.AUDIO_INFO:
        return renderAudioPreview();
      case PREVIEW_TYPES.VIDEO_INFO:
        return renderVideoPreview();
      case PREVIEW_TYPES.METADATA:
        // Check if this is a PDF that failed to load content
        return preview.isPdfPreview ? renderPdfMetadataPreview() : renderMetadataPreview();
      default:
        return renderMetadataPreview();
    }
  };

  const renderTextPreview = () => {
    if (!preview) return null;

    // Debug: show processed content and image URLs
    const baseContent = state.resolvedContent || preview.content;

    return (
      <div className="relative bg-white rounded-lg p-6 border border-[#E3E3E3] shadow-sm min-h-[400px]">
        {canCopy && (
          <div className="absolute top-4 right-4 z-10">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopyAsMarkdown}
              className="h-[32px] px-[12px] text-[12px] font-medium border-[#E3E3E3] text-[#1E1E1E] hover:bg-[#F5F5F5] bg-white shadow-sm"
            >
              {state.copyStatus === 'copied' ? (
                <>
                  <CheckCircle className="h-3.5 w-3.5 mr-1.5 text-green-600" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5 mr-1.5" />
                  Copy Markdown
                </>
              )}
            </Button>
          </div>
        )}
        <MarkdownContent content={baseContent} notebookId={notebookId} fileId={source.file_id || ''} />
      </div>
    );
  };

  const renderUrlPreview = () => {
    if (!preview) return null;

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-[#F7F7F7]">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-[#F5F5F5] flex items-center justify-center">
              <Globe className="h-5 w-5 text-[#1E1E1E]" />
            </div>
            <div>
              <h3 className="text-[16px] font-bold text-[#1E1E1E]">{preview.title}</h3>
              <div className="flex items-center space-x-2 mt-1">
                <Badge variant="secondary" className="bg-[#F5F5F5] text-[#666666] hover:bg-[#E3E3E3] border-0 rounded-sm px-2 py-0.5 text-[12px]">
                  {preview.processingType === 'media' ? 'Media' : 'Website'}
                </Badge>
                {preview.domain && (
                  <Badge variant="secondary" className="bg-[#F5F5F5] text-[#666666] hover:bg-[#E3E3E3] border-0 rounded-sm px-2 py-0.5 text-[12px]">
                    <Globe className="h-3 w-3 mr-1" />
                    {preview.domain}
                  </Badge>
                )}
                {preview.extractedAt && (
                  <Badge variant="secondary" className="bg-[#F5F5F5] text-[#666666] hover:bg-[#E3E3E3] border-0 rounded-sm px-2 py-0.5 text-[12px]">
                    <Calendar className="h-3 w-3 mr-1" />
                    {formatDate(preview.extractedAt)}
                  </Badge>
                )}
              </div>
            </div>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => window.open(preview?.url, '_blank')}
            className="h-[32px] px-[16px] text-[13px] font-medium border-[#E3E3E3] text-[#1E1E1E] hover:bg-[#F5F5F5]"
          >
            <ExternalLink className="h-3 w-3 mr-2" />
            Open Original
          </Button>
        </div>

        <div className="bg-white rounded-lg p-6 border border-[#E3E3E3] shadow-sm">
          <div className="mb-4">
            <span className="text-[12px] font-medium text-[#666666] uppercase tracking-wider">Source URL</span>
            <p className="text-[14px] text-[#2788D9] break-all mt-1 hover:underline cursor-pointer" onClick={() => window.open(preview?.url, '_blank')}>
              {preview?.url}
            </p>
          </div>

          {preview?.content && (
            <div>
              <span className="text-[12px] font-medium text-[#666666] uppercase tracking-wider">Content Preview</span>
              <p className="text-[14px] text-[#1E1E1E] mt-2 leading-[1.6]">{preview?.content}</p>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderAudioPreview = () => {
    if (!preview) return null;

    return (
      <div className="space-y-6">
        {/* Audio Player Section */}
        <div className="bg-[#F5F5F5] rounded-lg p-6 border border-[#E3E3E3]">
          <div className="flex items-center space-x-4 mb-4">
            <div className="w-12 h-12 bg-[#1E1E1E] rounded-full flex items-center justify-center">
              <Music className="h-6 w-6 text-white" />
            </div>
            <div className="flex-1">
              <h4 className="text-[16px] font-bold text-[#1E1E1E]">Audio Player</h4>
              <p className="text-[13px] text-[#666666]">Click play to listen to the audio file</p>
            </div>
          </div>

          {/* Audio Element */}
          <audio
            controls
            className="w-full h-10 rounded-lg"
            preload="metadata"
            controlsList="nodownload"
            onError={(e: React.SyntheticEvent<HTMLAudioElement>) => {
              console.error('Audio load error:', e);
              updateState({ audioError: true });
            }}
            onLoadedMetadata={() => {
              updateState({ audioLoaded: true, audioError: false });
            }}
            onCanPlay={() => {
              updateState({ audioLoaded: true, audioError: false });
            }}
          >
            <source
              src={preview.audioUrl}
              type={getAudioMimeType(preview.format)}
            />
            <source
              src={preview.audioUrl}
              type={`audio/${preview.format.toLowerCase()}`}
            />
            Your browser does not support the audio element.
          </audio>

          {state.audioError && (
            <div className="mt-3 flex items-center text-[12px] text-[#CE0E2D]">
              <AlertCircle className="h-3 w-3 mr-1.5" />
              Audio file could not be loaded
            </div>
          )}
        </div>

        {/* Transcript Content Display */}
        {preview.hasTranscript && (
          <div className="bg-white rounded-lg border border-[#E3E3E3] shadow-sm">
            <div className="p-4 border-b border-[#F7F7F7] flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-[#F5F5F5] rounded-full flex items-center justify-center">
                  <FileText className="h-4 w-4 text-[#1E1E1E]" />
                </div>
                <h4 className="text-[16px] font-bold text-[#1E1E1E]">Transcript</h4>
              </div>
            </div>
            <div className="p-6 max-h-[500px] overflow-y-auto">
              <MarkdownContent
                content={preview.content as string}
                notebookId={notebookId}
                fileId={source.file_id || ''}
              />
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderVideoPreview = () => {
    if (!preview) return null;

    return (
      <div className="space-y-6">
        {/* Video Player Section */}
        <div className="bg-black rounded-lg overflow-hidden shadow-md">
          <video
            controls
            className="w-full aspect-video"
            preload="metadata"
            controlsList="nodownload"
            onError={(e: React.SyntheticEvent<HTMLVideoElement>) => {
              console.error('Video load error:', e);
              updateState({ videoError: true });
            }}
            onLoadedMetadata={() => {
              updateState({ videoLoaded: true, videoError: false });
            }}
            onCanPlay={() => {
              updateState({ videoLoaded: true, videoError: false });
            }}
          >
            <source
              src={preview.videoUrl}
              type={getVideoMimeType(preview.format)}
            />
            <source
              src={preview.videoUrl}
              type={`video/${preview.format.toLowerCase()}`}
            />
            Your browser does not support the video element.
          </video>

          {state.videoError && (
            <div className="p-4 bg-[#FEF2F2] text-[#CE0E2D] text-[13px] flex items-center justify-center">
              <AlertCircle className="h-4 w-4 mr-2" />
              Video file could not be loaded
            </div>
          )}
        </div>

        {/* Transcript Content Display */}
        {preview.hasTranscript && (
          <div className="bg-white rounded-lg border border-[#E3E3E3] shadow-sm">
            <div className="p-4 border-b border-[#F7F7F7] flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-[#F5F5F5] rounded-full flex items-center justify-center">
                  <FileText className="h-4 w-4 text-[#1E1E1E]" />
                </div>
                <h4 className="text-[16px] font-bold text-[#1E1E1E]">Transcript</h4>
              </div>
            </div>
            <div className="p-6 max-h-[500px] overflow-y-auto">
              <MarkdownContent
                content={preview.content as string}
                notebookId={notebookId}
                fileId={source.file_id || ''}
              />
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderPdfContentPreview = () => {
    if (!preview) return null;

    // Process markdown content from the PDF
    const baseContent = state.resolvedContent || preview.content;
    const processedContent = baseContent;

    return (
      <div className="relative bg-white rounded-lg p-6 border border-[#E3E3E3] shadow-sm min-h-[400px]">
        {canCopy && (
          <div className="absolute top-4 right-4 z-10">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopyAsMarkdown}
              className="h-[32px] px-[12px] text-[12px] font-medium border-[#E3E3E3] text-[#1E1E1E] hover:bg-[#F5F5F5] bg-white shadow-sm"
            >
              {state.copyStatus === 'copied' ? (
                <>
                  <CheckCircle className="h-3.5 w-3.5 mr-1.5 text-green-600" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5 mr-1.5" />
                  Copy Markdown
                </>
              )}
            </Button>
          </div>
        )}
        {processedContent ? (
          <MarkdownContent content={processedContent} notebookId={notebookId} fileId={source.file_id || ''} />
        ) : (
          <div className="text-center py-8">
            <FileText className="h-12 w-12 text-[#B1B1B1] mx-auto mb-4" />
            <p className="text-[#666666] text-[14px]">No text content extracted from this PDF</p>
            <p className="text-[#999999] text-[13px] mt-2">Click "Open PDF" button to view the original file</p>
          </div>
        )}
      </div>
    );
  };

  const renderExcelContentPreview = () => {
    if (!preview) return null;

    const processedContent = preview.content as string;

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-[#F7F7F7]">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-[#F5F5F5] flex items-center justify-center">
              <FileSpreadsheet className="h-5 w-5 text-[#107C41]" />
            </div>
            <div>
              <h3 className="text-[16px] font-bold text-[#1E1E1E]">{preview.title}</h3>
              <div className="flex items-center space-x-2 mt-1">
                <Badge variant="secondary" className="bg-[#F5F5F5] text-[#666666] hover:bg-[#E3E3E3] border-0 rounded-sm px-2 py-0.5 text-[12px]">
                  Spreadsheet
                </Badge>
                {preview.fileSize && (
                  <Badge variant="secondary" className="bg-[#F5F5F5] text-[#666666] hover:bg-[#E3E3E3] border-0 rounded-sm px-2 py-0.5 text-[12px]">
                    <HardDrive className="h-3 w-3 mr-1" />
                    {preview.fileSize}
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="relative bg-white rounded-lg p-6 border border-[#E3E3E3] shadow-sm min-h-[400px] overflow-x-auto">
          {canCopy && (
            <div className="absolute top-4 right-4 z-10">
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyAsMarkdown}
                className="h-[32px] px-[12px] text-[12px] font-medium border-[#E3E3E3] text-[#1E1E1E] hover:bg-[#F5F5F5] bg-white shadow-sm"
              >
                {state.copyStatus === 'copied' ? (
                  <>
                    <CheckCircle className="h-3.5 w-3.5 mr-1.5 text-green-600" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5 mr-1.5" />
                    Copy Markdown
                  </>
                )}
              </Button>
            </div>
          )}
          <MarkdownContent content={processedContent} notebookId={notebookId} fileId={source.file_id || ''} />
        </div>
      </div>
    );
  };

  const renderMetadataPreview = () => {
    if (!preview) return null;

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-[#F7F7F7]">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-[#F5F5F5] flex items-center justify-center">
              <File className="h-5 w-5 text-[#666666]" />
            </div>
            <div>
              <h3 className="text-[16px] font-bold text-[#1E1E1E]">{preview.title}</h3>
              <div className="flex items-center space-x-2 mt-1">
                <Badge variant="secondary" className="bg-[#F5F5F5] text-[#666666] hover:bg-[#E3E3E3] border-0 rounded-sm px-2 py-0.5 text-[12px]">
                  {preview.format || 'Unknown Format'}
                </Badge>
                {preview.fileSize && (
                  <Badge variant="secondary" className="bg-[#F5F5F5] text-[#666666] hover:bg-[#E3E3E3] border-0 rounded-sm px-2 py-0.5 text-[12px]">
                    <HardDrive className="h-3 w-3 mr-1" />
                    {preview.fileSize}
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="bg-[#F5F5F5] rounded-lg p-8 text-center border border-[#E3E3E3]">
          <File className="h-16 w-16 text-[#B1B1B1] mx-auto mb-4" />
          <h4 className="text-[18px] font-medium text-[#1E1E1E] mb-2">Preview Not Available</h4>
          <p className="text-[#666666] text-[14px] max-w-md mx-auto">
            This file type cannot be previewed directly. You can download it to view locally.
          </p>
          <div className="mt-6">
            <Button
              variant="default"
              className="bg-[#000000] text-white hover:bg-[#333333] h-[40px] px-[24px] text-[13px] font-medium rounded-md"
              onClick={() => {
                const fileId = source.file_id || source.id;
                if (fileId) {
                  const url = getFileUrl(String(fileId), 'raw');
                  downloadFileSecurely(url, source.title || 'download');
                }
              }}
            >
              Download File
            </Button>
          </div>
        </div>
      </div>
    );
  };

  const renderPdfMetadataPreview = () => {
    // Fallback for PDF when content extraction fails but we have metadata
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-[#F7F7F7]">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-[#F5F5F5] flex items-center justify-center">
              <FileText className="h-5 w-5 text-[#CE0E2D]" />
            </div>
            <div>
              <h3 className="text-[16px] font-bold text-[#1E1E1E]">{preview?.title || source.title}</h3>
              <div className="flex items-center space-x-2 mt-1">
                <Badge variant="secondary" className="bg-[#F5F5F5] text-[#666666] hover:bg-[#E3E3E3] border-0 rounded-sm px-2 py-0.5 text-[12px]">
                  PDF Document
                </Badge>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-[#F5F5F5] rounded-lg p-8 text-center border border-[#E3E3E3]">
          <FileText className="h-16 w-16 text-[#B1B1B1] mx-auto mb-4" />
          <h4 className="text-[18px] font-medium text-[#1E1E1E] mb-2">Preview Unavailable</h4>
          <p className="text-[#666666] text-[14px] max-w-md mx-auto mb-6">
            We couldn't load the preview for this PDF. You can try opening it in a new tab or downloading it.
          </p>
          <div className="flex items-center justify-center space-x-4">
            <Button
              variant="outline"
              className="h-[40px] px-[24px] text-[13px] font-medium border-[#E3E3E3] text-[#1E1E1E] hover:bg-[#F5F5F5]"
              onClick={() => {
                // Try to construct a direct URL
                const fileId = source.file_id || source.id;
                if (fileId) {
                  const url = getFileUrl(String(fileId), 'inline');
                  window.open(url, '_blank');
                }
              }}
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              Open in New Tab
            </Button>
            <Button
              variant="default"
              className="bg-[#000000] text-white hover:bg-[#333333] h-[40px] px-[24px] text-[13px] font-medium rounded-md"
              onClick={() => {
                const fileId = source.file_id || source.id;
                if (fileId) {
                  const url = getFileUrl(String(fileId), 'raw');
                  downloadFileSecurely(url, source.title || 'download');
                }
              }}
            >
              Download PDF
            </Button>
          </div>
        </div>
      </div>
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 sm:p-6">
      <div
        className={`bg-white rounded-xl shadow-2xl w-full h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200 transition-[max-width] ease-in-out ${state.hasGalleryImages ? 'max-w-[90vw]' : 'max-w-5xl'
          }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#F7F7F7] bg-white shrink-0">
          <div className="flex items-center space-x-3 overflow-hidden">
            <div className="p-2 bg-[#F5F5F5] rounded-lg shrink-0">
              {React.createElement(getPreviewIcon(preview?.type || PREVIEW_TYPES.METADATA), {
                className: "h-5 w-5 text-[#1E1E1E]"
              })}
            </div>
            <div className="min-w-0">
              <h2 className="text-[18px] font-bold text-[#1E1E1E] truncate">
                {source.title}
              </h2>
              <p className="text-[12px] text-[#666666] truncate">
                {source.ext?.toUpperCase() || 'FILE'} • {formatDate(source.createdAt)}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2 shrink-0 ml-4">
            {shouldShowOpenDocument && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleOpenDocument}
                className="h-[32px] px-[12px] text-[12px] font-medium border-[#E3E3E3] text-[#1E1E1E] hover:bg-[#F5F5F5]"
              >
                <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                Open Document
              </Button>
            )}
            {preview?.isPdfPreview && preview?.pdfUrl && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.open(preview?.pdfUrl, '_blank')}
                className="h-[32px] px-[12px] text-[12px] font-medium border-[#E3E3E3] text-[#1E1E1E] hover:bg-[#F5F5F5]"
              >
                <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                Open PDF
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="h-8 w-8 rounded-full hover:bg-[#F5F5F5] text-[#666666] hover:text-[#1E1E1E]"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
        </div>

        {/* Content Body - Flex Row */}
        <div className="flex-1 flex overflow-hidden min-h-0">
          {/* Main Content */}
          <div className="flex-1 overflow-y-auto p-6 sm:p-8 bg-white">
            {renderPreviewContent()}
          </div>

          {/* Side Gallery Panel */}
          {preview?.type === PREVIEW_TYPES.TEXT_CONTENT && (
            <div
              className={`border-l border-[#F7F7F7] bg-[#F9FAFB] transition-all duration-300 ease-in-out flex flex-col ${state.hasGalleryImages ? 'w-[26rem] p-4 opacity-100' : 'w-0 p-0 opacity-0 overflow-hidden border-none'
                }`}
            >
              <div className="w-full h-full overflow-hidden"> {/* Full width/height container */}
                <GallerySection
                  notebookId={notebookId}
                  videoFileId={source.file_id || ''}
                  onOpenModal={openModal}
                  onCloseModal={closeModal}
                  onImagesLoaded={(hasImages) => updateState({ hasGalleryImages: hasImages })}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FilePreview;
