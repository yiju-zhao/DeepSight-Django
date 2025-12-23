// Notebook components index
// Organized exports for all notebook-specific components

// Layout components
export { default as NotebookLayout } from './layout/NotebookLayout';
export { default as NotebookHeader } from './layout/NotebookHeader';
export { default as NotebookChatContainer } from './layout/NotebookChatContainer';

// Panel components
export { default as SessionChatPanel } from './panels/SessionChatPanel';
export { default as SourcesPanel } from './panels/SourcesPanel';
export { default as StudioPanel } from './panels/StudioPanel';

// Source management components
export { default as SourcesList } from './sources/SourcesList';
export { default as AddSourceModal } from './sources/AddSourceModal';

// Studio components
export { default as StudioPanelMain } from './studio/StudioPanel';
export { default as PodcastAudioPlayer } from './studio/PodcastAudioPlayer';
// export { default as PodcastGenerationForm } from './studio/PodcastGenerationForm';
// export { default as ReportGenerationForm } from './studio/ReportGenerationForm';

export { default as CustomizeModal } from './studio/CustomizeModal';
export { default as FileViewer } from './studio/FileViewer';
export { default as AuthenticatedImage } from './studio/AuthenticatedImage';

// Shared components
export { default as FilePreview } from './shared/FilePreview';
export { default as GallerySection } from './shared/GallerySection';

// Modern components
export { NotebookGrid } from './modern/NotebookGrid';
export { default as NotebookGridModernContainer } from './modern/NotebookGridModernContainer';

export { default as CreateNotebookForm } from './CreateNotebookForm';

// Utility components
export { default as ChatErrorBoundary } from './utils/ChatErrorBoundary';

// Types and utilities
export * from './studio/types';
