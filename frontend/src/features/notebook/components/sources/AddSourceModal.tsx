import React, { useState, useRef, useCallback } from "react";
import { X, Upload, Link2, FileText, Globe, Youtube, Loader2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import sourceService from "@/features/notebook/services/SourceService";
import { COLORS } from "@/features/notebook/config/uiConfig";


interface AddSourceModalProps {
  onClose: () => void;
  notebookId: string;
  onSourcesAdded: () => void;
  onUploadStarted?: (fileId: string, filename: string, fileType: string) => void;
  onKnowledgeBaseItemsDeleted?: () => void;
}

const AddSourceModal: React.FC<AddSourceModalProps> = ({
  onClose,
  notebookId,
  onSourcesAdded,
  onUploadStarted,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [urlInput, setUrlInput] = useState('');
  const [pasteText, setPasteText] = useState('');
  const [activeTab, setActiveTab] = useState('file');
  const [urlProcessingType, setUrlProcessingType] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [batchResults, setBatchResults] = useState<{
    successful: Array<{ url: string; file_id: string }>;
    failed: Array<{ url: string; reason: string }>;
  } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // URL parsing function for batch mode
  const parseUrls = (text: string): string[] => {
    return text
      .split('\n')
      .map(url => url.trim())
      .filter(url => url.length > 0 && (url.startsWith('http://') || url.startsWith('https://')));
  };

  // File validation function
  const validateFile = (file: File) => {
    const allowedExtensions = ["pdf", "txt", "md", "ppt", "pptx", "doc", "docx", "xlsx", "xls", "mp3", "mp4", "wav", "m4a", "avi", "mov", "mkv", "webm", "wmv", "m4v"];
    const extension = file.name.split(".").pop()?.toLowerCase() || "";
    const maxSize = 100 * 1024 * 1024; // 100MB
    const minSize = 100; // 100 bytes minimum
    const errors = [];
    if (!extension) {
      errors.push("File must have an extension");
    } else if (!allowedExtensions.includes(extension)) {
      errors.push(`File type "${extension}" is not supported. Allowed types: ${allowedExtensions.join(", ")}`);
    }
    if (file.size > maxSize) {
      errors.push(`File size (${(file.size / (1024 * 1024)).toFixed(1)}MB) exceeds maximum allowed size of 100MB`);
    } else if (file.size < minSize) {
      errors.push("File is very small and may be empty");
    }
    if (/[<>:"|?*]/.test(file.name)) {
      errors.push("Filename contains invalid characters");
    }
    return { valid: errors.length === 0, errors, extension };
  };

  // Handle file upload
  const handleFileUpload = async (file: File) => {
    const validation = validateFile(file);
    if (!validation.valid) {
      setError(`File validation failed: ${validation.errors.join(', ')}`);
      return;
    }
    setError(null);
    setIsUploading(true);
    try {
      const uploadFileId = `upload_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;

      // Send API request first to get the real file_id
      const response = await sourceService.parseFile(file, uploadFileId, notebookId);

      if (response.success) {
        // Use the REAL file_id from API response (database primary key)
        const realFileId = response.file_id || uploadFileId;
        console.log(`File uploaded successfully with file_id: ${realFileId}`);

        // Notify parent with the real file_id (ONLY ONCE)
        if (onUploadStarted) {
          onUploadStarted(realFileId, file.name, validation.extension);
        }

        // Close modal and refresh sources list on success
        handleClose();
        onSourcesAdded();
      } else {
        throw new Error(response.error || 'Upload failed');
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      // Check if this is a validation error (duplicate file)
      if (errorMessage.includes('already exists')) {
        // This is a validation error - keep modal open and show error
        // The item will show as "failed" in the processing list, which is appropriate
        setError(`File "${file.name}" already exists in this workspace. Please choose a different file or rename it.`);
        // Don't close modal, let user try again or cancel
      } else {
        // This is a processing error - close modal and let processing system handle it
        handleClose();
        // The processing system will show the error state in the processing list
        console.error(`Processing error for ${file.name}:`, errorMessage);
      }
    } finally {
      setIsUploading(false);
    }
  };

  // Handle link upload
  const handleLinkUpload = async () => {
    const urls = parseUrls(urlInput);

    if (urls.length === 0) {
      setError('Please enter at least one valid URL (one per line, starting with http:// or https://)');
      return;
    }

    setError(null);
    setIsUploading(true);
    setBatchResults(null);

    // Single URL mode handling
    if (urls.length === 1) {
      const singleUrl = urls[0];
      if (!singleUrl) {
        setError('Invalid URL provided.');
        setIsUploading(false);
        return;
      }
      try {
        const uploadFileId = `link_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
        // Get display name for URL
        const urlDomain = singleUrl.replace(/^https?:\/\//, '').split('/')[0];
        const displayName = `${urlDomain} - ${urlProcessingType || 'website'}`;

        // Send API request to get the real file_id
        let response;
        if (urlProcessingType === 'media') {
          response = await sourceService.parseUrlWithMedia(singleUrl, notebookId, 'cosine', uploadFileId);
        } else if (urlProcessingType === 'document') {
          response = await sourceService.parseDocumentUrl(singleUrl, notebookId, 'cosine', uploadFileId);
        } else {
          response = await sourceService.parseUrl(singleUrl, notebookId, 'cosine', uploadFileId);
        }

        if (response.success) {
          // Use the REAL file_id from API response
          const realFileId = response.file_id || uploadFileId;
          console.log(`URL added successfully with file_id: ${realFileId}`);

          // Notify parent with the real file_id (ONLY ONCE)
          if (onUploadStarted) {
            onUploadStarted(realFileId, displayName, 'url');
          }

          // Close modal
          handleClose();
        } else {
          throw new Error(response.error || 'URL parsing failed');
        }
      } catch (error) {
        console.error('Error processing URL:', error);
        // Parse the error message to check for duplicate URL detection
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        // Check if this is a duplicate URL validation error
        if (errorMessage.includes('already exists')) {
          // This is a validation error - keep modal open and show error
          // The item will show as "failed" in the processing list, which is appropriate
          setError(`This URL already exists in your workspace. Please use a different URL.`);
          // Don't close modal, let user try again or cancel
        } else {
          // This is a processing error - close modal and let processing system handle it
          handleClose();
          // The processing system will show the error state in the processing list
          console.error(`Processing error for ${singleUrl}:`, errorMessage);
        }
      } finally {
        setIsUploading(false);
      }
      return;
    }

    // Batch mode handling (multiple URLs)
    try {
      const uploadFileId = `link_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;

      // Call batch API based on processing type
      let response;
      if (urlProcessingType === 'media') {
        response = await sourceService.parseUrlWithMedia(urls, notebookId, 'cosine', uploadFileId);
      } else if (urlProcessingType === 'document') {
        response = await sourceService.parseDocumentUrl(urls, notebookId, 'cosine', uploadFileId);
      } else {
        response = await sourceService.parseUrl(urls, notebookId, 'cosine', uploadFileId);
      }

      // Handle batch response
      if (response.successful || response.failed) {
        const results = {
          successful: response.successful || [],
          failed: response.failed || []
        };
        setBatchResults(results);

        // Notify parent for each successful upload
        if (onUploadStarted && results.successful.length > 0) {
          results.successful.forEach((item: { url: string; file_id: string }) => {
            const urlDomain = item.url.replace(/^https?:\/\//, '').split('/')[0];
            const displayName = `${urlDomain} - ${urlProcessingType || 'website'}`;
            onUploadStarted(item.file_id, displayName, 'url');
          });
        }

        // If all succeeded, close modal
        if (results.failed.length === 0) {
          setTimeout(() => {
            handleClose();
            onSourcesAdded();
          }, 1500);
        }
      } else {
        throw new Error(response.error || 'Batch URL parsing failed');
      }
    } catch (error) {
      console.error('Error processing batch URLs:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setError(`Failed to process URLs: ${errorMessage}`);
    } finally {
      setIsUploading(false);
    }
  };

  // Handle text upload
  const handleTextUpload = async () => {
    if (!pasteText.trim()) {
      setError('Please enter some text content');
      return;
    }

    setError(null);
    setIsUploading(true);
    try {
      const uploadFileId = `text_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
      // Generate filename from first 5 words
      const words = pasteText.trim()
        .split(/\s+/)
        .slice(0, 5)
        .map((word: string) => word.replace(/[^a-zA-Z0-9]/g, ''))
        .filter((word: string) => word.length > 0);
      const filename = words.length > 0 ? `${words.join('_').toLowerCase()}.md` : 'pasted_text.md';
      const blob = new Blob([pasteText], { type: 'text/markdown' });
      const file = new File([blob], filename, { type: 'text/markdown' });

      // Send API request to get the real file_id
      const response = await sourceService.parseFile(file, uploadFileId, notebookId);

      if (response.success) {
        // Use the REAL file_id from API response
        const realFileId = response.file_id || uploadFileId;
        console.log(`Text uploaded successfully with file_id: ${realFileId}`);

        // Notify parent with the real file_id (ONLY ONCE)
        if (onUploadStarted) {
          onUploadStarted(realFileId, filename, 'md');
        }

        // Close modal and refresh sources list
        handleClose();
        onSourcesAdded();
      } else {
        throw new Error(response.error || 'Text upload failed');
      }
    } catch (error) {
      console.error('Error processing text:', error);
      // Parse the error message to check for duplicate content detection
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      // Check if this is a duplicate content validation error
      if (errorMessage.includes('already exists') || errorMessage.includes('Duplicate content detected')) {
        setError(`This text content already exists in your workspace. Please modify the text or use different content.`);
      } else {
        setError(`Failed to upload text: ${errorMessage}`);
      }
    } finally {
      setIsUploading(false);
    }
  };




  // Drag and drop handlers
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      const file = files[0];
      if (file) {
        handleFileUpload(file);
      }
    }
  }, []);

  // Handle modal close
  const handleClose = () => {
    setActiveTab('file');
    setUrlInput('');
    setPasteText('');
    setBatchResults(null);
    setError(null);
    setIsUploading(false);
    onClose();
  };

  return (
    <>
      {/* Header - Fixed at top */}
      <div className="sticky top-0 z-50 bg-white pt-6 pb-4 px-8 border-b border-[#F7F7F7]">
        <div className="flex items-center justify-between mb-1">
          <div>
            <h2 className="text-[20px] font-bold text-[#1E1E1E]">Add Source</h2>
            <p className="text-[14px] text-[#666666] mt-1">Add files, links, or text to this notebook</p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              handleClose();
            }}
            className="h-8 w-8 text-[#B1B1B1] hover:text-[#666666] hover:bg-[#F5F5F5] rounded-full transition-colors"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Custom Error Display */}
        {error && (
          <div className="mt-4 p-3 bg-[#FEF2F2] border border-[#FCA5A5] rounded-lg flex items-start">
            <div className="flex-shrink-0 mt-0.5">
              <svg className="h-4 w-4 text-[#CE0E2D]" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3 flex-1 text-[13px] text-[#991B1B] leading-5">
              {error}
            </div>
            <button
              type="button"
              className="ml-3 flex-shrink-0 text-[#EF4444] hover:text-[#991B1B]"
              onClick={() => setError(null)}
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>

      {/* Main Upload Area */}
      <div
        className={`border-2 border-dashed rounded-2xl p-8 mb-8 text-center transition-all duration-200 mt-8 mx-8 ${isDragOver
          ? 'border-[#CE0E2D] bg-[#FEF2F2]'
          : 'border-[#E3E3E3] bg-[#F9FAFB] hover:border-[#B1B1B1]'
          }`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <div className="flex flex-col items-center space-y-3">
          <div className={`w-12 h-12 bg-[#CE0E2D] rounded-full flex items-center justify-center shadow-md`}>
            <Upload className="h-6 w-6 text-white" />
          </div>
          <div>
            <h3 className="text-[16px] font-bold text-[#1E1E1E] mb-1">Upload sources</h3>
            <p className="text-[14px] text-[#666666]">
              Drag & drop or{' '}
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  fileInputRef.current?.click();
                }}
                className="text-[#CE0E2D] hover:text-[#A30B24] font-medium hover:underline transition-colors"
                disabled={isUploading}
              >
                choose file to upload
              </button>
            </p>
          </div>
        </div>
        <p className="text-[12px] text-[#999999] mt-4 max-w-md mx-auto leading-relaxed">
          Supported file types: pdf, txt, markdown, pptx, docx, Audio (mp3, wav, m4a), Video (mp4, avi, mov, mkv, webm, wmv, m4v)
        </p>
      </div>

      {/* Upload Options */}
      <div className="space-y-6 pb-8 px-8">
        {/* Link Section */}
        <div className="bg-white border border-[#E3E3E3] rounded-2xl p-6 shadow-[0_2px_8px_rgba(0,0,0,0.04)]">
          <div className="flex items-center space-x-3 mb-5">
            <div className="w-8 h-8 bg-[#CE0E2D] rounded-lg flex items-center justify-center">
              <Link2 className="h-4 w-4 text-white" />
            </div>
            <h3 className="text-[16px] font-bold text-[#1E1E1E]">Link</h3>
          </div>

          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <button
                className={`flex items-center justify-center space-x-2 p-2.5 rounded-lg transition-all duration-200 border ${urlProcessingType === 'website'
                  ? 'bg-[#CE0E2D] border-[#CE0E2D] text-white shadow-md'
                  : 'bg-white border-[#E3E3E3] text-[#666666] hover:bg-[#F5F5F5] hover:text-[#1E1E1E]'
                  }`}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setActiveTab('link');
                  setUrlProcessingType('website');
                }}
                disabled={isUploading}
              >
                <Globe className="h-4 w-4" />
                <span className="text-[13px] font-medium">Website</span>
              </button>
              <button
                className={`flex items-center justify-center space-x-2 p-2.5 rounded-lg transition-all duration-200 border ${urlProcessingType === 'document'
                  ? 'bg-[#CE0E2D] border-[#CE0E2D] text-white shadow-md'
                  : 'bg-white border-[#E3E3E3] text-[#666666] hover:bg-[#F5F5F5] hover:text-[#1E1E1E]'
                  }`}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setActiveTab('link');
                  setUrlProcessingType('document');
                }}
                disabled={isUploading}
              >
                <FileText className="h-4 w-4" />
                <span className="text-[13px] font-medium">Document</span>
              </button>
              <button
                className={`flex items-center justify-center space-x-2 p-2.5 rounded-lg transition-all duration-200 border ${urlProcessingType === 'media'
                  ? 'bg-[#CE0E2D] border-[#CE0E2D] text-white shadow-md'
                  : 'bg-white border-[#E3E3E3] text-[#666666] hover:bg-[#F5F5F5] hover:text-[#1E1E1E]'
                  }`}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setActiveTab('link');
                  setUrlProcessingType('media');
                }}
                disabled={isUploading}
              >
                <Youtube className="h-4 w-4" />
                <span className="text-[13px] font-medium">Video</span>
              </button>
            </div>

            {activeTab === 'link' && (
              <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
                <textarea
                  placeholder={`Enter one or more URLs (one per line)${urlProcessingType === 'media'
                    ? '\nExample:\nhttps://youtube.com/watch?v=...\nhttps://vimeo.com/...'
                    : urlProcessingType === 'document'
                      ? '\nExample:\nhttps://example.com/doc1.pdf\nhttps://example.com/doc2.pptx'
                      : '\nExample:\nhttps://example.com/article1\nhttps://example.com/article2'
                    }`}
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  rows={5}
                  className="w-full p-4 bg-[#F9FAFB] border border-[#E3E3E3] rounded-xl text-[#1E1E1E] placeholder-[#999999] focus:outline-none focus:ring-1 focus:ring-[#CE0E2D] focus:border-[#CE0E2D] resize-none font-mono text-[13px] transition-all"
                  disabled={isUploading}
                />
                <div className="flex items-center justify-between text-[12px] text-[#666666] px-1">
                  <span>{parseUrls(urlInput).length} valid URLs</span>
                  <span>{urlInput.split('\n').length} lines</span>
                </div>

                {/* Batch Results Display */}
                {batchResults && (
                  <div className="space-y-2 p-4 bg-[#F9FAFB] border border-[#E3E3E3] rounded-xl">
                    <div className="text-[13px] font-medium text-[#1E1E1E]">
                      Results: {batchResults.successful.length} succeeded, {batchResults.failed.length} failed
                    </div>
                    {batchResults.successful.length > 0 && (
                      <div className="text-[12px] text-emerald-600">
                        ✓ {batchResults.successful.length} URL{batchResults.successful.length > 1 ? 's' : ''} added successfully
                      </div>
                    )}
                    {batchResults.failed.length > 0 && (
                      <div className="space-y-1">
                        <div className="text-[12px] font-medium text-[#CE0E2D]">
                          ✗ Failed URLs:
                        </div>
                        {batchResults.failed.slice(0, 3).map((item, idx) => (
                          <div key={idx} className="text-[12px] text-[#CE0E2D] pl-3">
                            • {item.url}: {item.reason}
                          </div>
                        ))}
                        {batchResults.failed.length > 3 && (
                          <div className="text-[12px] text-[#666666] pl-3">
                            ... and {batchResults.failed.length - 3} more
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                <Button
                  onClick={handleLinkUpload}
                  disabled={parseUrls(urlInput).length === 0 || isUploading}
                  className="w-full h-10 bg-[#CE0E2D] hover:bg-[#A30B24] text-white rounded-lg font-medium transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isUploading ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : null}
                  {parseUrls(urlInput).length > 1
                    ? `Process ${parseUrls(urlInput).length} URL${parseUrls(urlInput).length !== 1 ? 's' : ''}`
                    : urlProcessingType === 'media'
                      ? 'Process Media'
                      : urlProcessingType === 'document'
                        ? 'Process Document'
                        : 'Process Website'}
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Paste Text Section */}
        <div className="bg-white border border-[#E3E3E3] rounded-2xl p-6 shadow-[0_2px_8px_rgba(0,0,0,0.04)]">
          <div className="flex items-center space-x-3 mb-5">
            <div className="w-8 h-8 bg-[#CE0E2D] rounded-lg flex items-center justify-center">
              <FileText className="h-4 w-4 text-white" />
            </div>
            <h3 className="text-[16px] font-bold text-[#1E1E1E]">Paste text</h3>
          </div>

          <div className="space-y-4">
            <button
              className={`w-full flex items-center justify-center space-x-2 p-2.5 rounded-lg transition-all duration-200 border ${activeTab === 'text'
                ? 'bg-[#CE0E2D] border-[#CE0E2D] text-white shadow-md'
                : 'bg-white border-[#E3E3E3] text-[#666666] hover:bg-[#F5F5F5] hover:text-[#1E1E1E]'
                }`}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setActiveTab('text');
                setUrlProcessingType('');
              }}
              disabled={isUploading}
            >
              <FileText className="h-4 w-4" />
              <span className="text-[13px] font-medium">Copied text</span>
            </button>

            {activeTab === 'text' && (
              <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
                <textarea
                  placeholder="Paste your text content here..."
                  value={pasteText}
                  onChange={(e) => setPasteText(e.target.value)}
                  maxLength={10000}
                  rows={6}
                  className="w-full p-4 bg-[#F9FAFB] border border-[#E3E3E3] rounded-xl text-[#1E1E1E] placeholder-[#999999] focus:outline-none focus:ring-1 focus:ring-[#CE0E2D] focus:border-[#CE0E2D] resize-none text-[14px] transition-all"
                  disabled={isUploading}
                />
                <div className="flex items-center justify-between text-[12px] text-[#666666] px-1">
                  <span>{pasteText.length} characters</span>
                  <span>{pasteText.length} / 10000</span>
                </div>
                <Button
                  onClick={handleTextUpload}
                  disabled={!pasteText.trim() || isUploading}
                  className="w-full h-10 bg-[#CE0E2D] hover:bg-[#A30B24] text-white rounded-lg font-medium transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isUploading ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <FileText className="h-4 w-4 mr-2" />
                  )}
                  Upload Text
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (!file) return;
          handleFileUpload(file);
        }}
        style={{ display: 'none' }}
        accept=".pdf,.txt,.md,.ppt,.pptx,.doc,.docx,.xlsx,.xls,.mp3,.mp4,.wav,.m4a,.avi,.mov,.mkv,.webm,.wmv,.m4v"
      />
    </>
  );
};

export default AddSourceModal;
