import React from 'react';
import { NotebookGrid as ModernNotebookGrid } from '@/features/notebook/components/modern/NotebookGrid';

// Thin container to mount the modern NotebookGrid as a page section
const NotebookGridModernContainer: React.FC = () => {
  return <ModernNotebookGrid />;
};

export default NotebookGridModernContainer;

