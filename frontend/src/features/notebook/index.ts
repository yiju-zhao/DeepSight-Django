// Main Components
export { default as DeepdivePage } from './pages/DeepdivePage';
export { default as NotebookListPage } from './pages/NotebookListPage';

// Layout Components
export { default as NotebookLayout } from './components/layout/NotebookLayout';
export { default as NotebookHeader } from './components/layout/NotebookHeader';

// Main Panels
export { default as SourcesPanel } from './components/panels/SourcesPanel';
export { default as SessionChatPanel } from './components/panels/SessionChatPanel';
export { default as StudioPanel } from './components/panels/StudioPanel';

// UI Components
export { default as CreateNotebookForm } from './components/CreateNotebookForm';
export { NotebookGrid } from './components/modern/NotebookGrid';
export { default as FilePreview } from './components/shared/FilePreview';

// Individual Panel Components (for direct access if needed)
export { default as SourcesList } from './components/sources/SourcesList';
export { default as Chat } from './components/panels/SessionChatPanel';
export { default as Studio } from './components/studio/StudioPanel';

// Hooks
export { useFileUpload } from './hooks/file/useFileUpload';
export { useFileSelection } from './hooks/file/useFileSelection';
export { useFileStatusSSE } from './hooks/file/useFileStatusSSE';

// Services (keeping these for now as they have consumers)
export { default as SourceService } from './services/SourceService';

// API - Backward compatible combined API
export { notebooksApi } from './api';

// Query Hooks - From the new modular structure
export * from './hooks/api';

// Configuration - From the new modular structure  
export * from './config';

// Types - From the new modular structure
export * from './types';

// Download utilities
export { downloadWithRedirect, triggerBlobDownload, triggerUrlDownload, downloadReportFile, downloadReportPdf, downloadPodcastAudio } from './utils/download';
