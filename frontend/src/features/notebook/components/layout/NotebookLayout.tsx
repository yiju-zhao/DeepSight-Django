import React, { useState, useRef, useCallback, ReactElement } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, Database, RectangleHorizontal } from "lucide-react";
import { Toaster } from "@/shared/components/ui/toaster";
import { Button } from "@/shared/components/ui/button";
import { LAYOUT_RATIOS, COLORS, SHADOWS, RESPONSIVE_PANELS, PANEL_HEADERS } from "@/features/notebook/config/uiConfig";
import NotebookHeader from "@/features/notebook/components/layout/NotebookHeader";
import { NotebookSettingsProvider } from "@/features/notebook/contexts/NotebookSettingsContext";
import NotebookSettingsModal from "@/features/notebook/components/modals/NotebookSettingsModal";

interface ModalState {
  isOpen: boolean;
  data: ReactElement | null;
}

interface ModalsState {
  filePreview: ModalState;
  uploadModal: ModalState;
  addSourceModal: ModalState;

  gallerySettings: ModalState;
  customizeReport: ModalState;
  customizePodcast: ModalState;
  notebookSettings: ModalState;
}

interface NotebookLayoutProps {
  notebookId: string;
  notebookTitle?: string;
  sourcesPanel: ReactElement;
  chatPanel: ReactElement;
  studioPanel: ReactElement;
  onSourcesSelectionChange?: () => void;
  sourcesRemovedTrigger?: number;
}

/**
 * Layout component for notebook pages
 * Handles responsive layout with collapsible panels and global modal management
 */
const NotebookLayout: React.FC<NotebookLayoutProps> = ({
  notebookId,
  notebookTitle,
  sourcesPanel,
  chatPanel,
  studioPanel,
  onSourcesSelectionChange,
  sourcesRemovedTrigger
}) => {
  const [isSourcesCollapsed, setIsSourcesCollapsed] = useState(false);
  const [isStudioExpanded, setIsStudioExpanded] = useState(false);
  const sourcesListRef = useRef<any>(null);
  const selectionChangeCallbackRef = useRef<(() => void) | null>(null);

  // Modal state management
  const [modals, setModals] = useState<ModalsState>({
    filePreview: { isOpen: false, data: null },
    uploadModal: { isOpen: false, data: null },
    addSourceModal: { isOpen: false, data: null },

    gallerySettings: { isOpen: false, data: null },
    customizeReport: { isOpen: false, data: null },
    customizePodcast: { isOpen: false, data: null },
    notebookSettings: { isOpen: false, data: null }
  });

  // Handle selection changes from SourcesList
  const handleSelectionChange = useCallback(() => {
    if (selectionChangeCallbackRef.current) {
      selectionChangeCallbackRef.current();
    }
  }, []);

  // Function to register callback from panels
  const registerSelectionCallback = useCallback((callback: () => void) => {
    selectionChangeCallbackRef.current = callback;
  }, []);

  // Modal management functions
  const openModal = useCallback((modalType: keyof ModalsState, data: ReactElement | null = null) => {
    setModals(prev => ({
      ...prev,
      [modalType]: { isOpen: true, data }
    }));
  }, []);

  const closeModal = useCallback((modalType: keyof ModalsState) => {
    setModals(prev => ({
      ...prev,
      [modalType]: { isOpen: false, data: null }
    }));
  }, []);

  // Handle studio expand/collapse
  const handleStudioToggleExpand = useCallback(() => {
    setIsStudioExpanded(prev => !prev);
  }, []);

  // Pass modal functions to panels
  const panelProps = {
    sourcesListRef,
    onSelectionChange: registerSelectionCallback,
    onOpenModal: openModal,
    onCloseModal: closeModal,
    sourcesRemovedTrigger
  };

  return (
    <NotebookSettingsProvider>
      <div className="h-screen bg-white flex flex-col relative overflow-hidden">
        {/* Header */}
        <NotebookHeader
          notebookTitle={notebookTitle}
          showBackButton={false}
          onOpenSettings={() => openModal('notebookSettings')}
        />

        {/* Main Content */}
        <main className="flex-1 flex flex-col min-h-0 bg-[#F5F5F5] overflow-hidden">
          <div
            className={`w-full max-w-[1920px] mx-auto h-full ${RESPONSIVE_PANELS.mobile.gap} ${RESPONSIVE_PANELS.mobile.padding} md:${RESPONSIVE_PANELS.tablet.gap} md:${RESPONSIVE_PANELS.tablet.padding} lg:${RESPONSIVE_PANELS.desktop.gap} lg:${RESPONSIVE_PANELS.desktop.padding} grid transition-[grid-template-columns] duration-300 ease-out`}
            style={{
              gridTemplateColumns: isStudioExpanded
                ? `56px 5fr 7fr` // Studio expanded: wider collapsed bar, balanced chat and studio
                : isSourcesCollapsed
                  ? `56px ${LAYOUT_RATIOS.chat}fr ${LAYOUT_RATIOS.studio}fr`
                  : `${LAYOUT_RATIOS.sources}fr ${LAYOUT_RATIOS.chat}fr ${LAYOUT_RATIOS.studio}fr`
            }}
          >
            {/* Sources Panel */}
            <div className={`bg-white ${RESPONSIVE_PANELS.desktop.radius} ${SHADOWS.panel.base} transition-all duration-300 overflow-hidden min-h-0 relative flex flex-col`}>
              {!isSourcesCollapsed && !isStudioExpanded ? (
                <div className="h-full flex flex-col">
                  {React.cloneElement(sourcesPanel, {
                    ...panelProps,
                    ref: sourcesListRef,
                    onToggleCollapse: () => setIsSourcesCollapsed(true),
                    isCollapsed: isSourcesCollapsed,
                    onSelectionChange: handleSelectionChange
                  })}
                </div>
              ) : (
                <div className="h-full flex flex-col">
                  {/* Collapsed Header - Entire bar clickable with subtle highlight */}
                  <div
                    className="flex-shrink-0 py-4 bg-white flex items-center justify-center h-full w-full cursor-pointer transition-all duration-200 group hover:bg-gray-50"
                    onClick={() => {
                      if (isStudioExpanded) {
                        setIsStudioExpanded(false);
                      }
                      setIsSourcesCollapsed(false);
                    }}
                    title={isStudioExpanded ? "Minimize Studio & Expand Sources Panel" : "Expand Sources Panel"}
                  >
                    <Database className="h-5 w-5 text-[#7F7F7F] group-hover:text-[#1E1E1E] transition-all duration-200" />
                  </div>
                </div>
              )}
            </div>

            {/* Chat Panel */}
            <div className={`bg-white ${RESPONSIVE_PANELS.desktop.radius} ${SHADOWS.panel.base} transition-all duration-300 overflow-hidden min-h-0 flex flex-col`}>
              {React.cloneElement(chatPanel, panelProps)}
            </div>

            {/* Studio Panel */}
            <div className={`bg-white ${RESPONSIVE_PANELS.desktop.radius} ${SHADOWS.panel.base} transition-all duration-300 overflow-hidden min-h-0 flex flex-col`}>
              {React.cloneElement(studioPanel, {
                ...panelProps,
                onToggleExpand: handleStudioToggleExpand,
                isStudioExpanded: isStudioExpanded
              })}
            </div>
          </div>
        </main>

        {/* Global Modals - Rendered at top level with consistent styling */}
        <AnimatePresence>
          {/* File Preview Modal */}
          {modals.filePreview.isOpen && modals.filePreview.data && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 flex items-center justify-center z-[100] p-4"
              onClick={() => closeModal('filePreview')}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                transition={{ type: "spring", duration: 0.3 }}
                className="bg-white rounded-xl shadow-xl max-w-5xl w-full max-h-[95vh] overflow-hidden"
                onClick={(e) => e.stopPropagation()}
              >
                {modals.filePreview.data}
              </motion.div>
            </motion.div>
          )}

          {/* Upload Modal */}
          {modals.uploadModal.isOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 flex items-center justify-center z-[100] p-4"
              onClick={() => closeModal('uploadModal')}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                transition={{ type: "spring", duration: 0.3 }}
                className="bg-gray-900 rounded-2xl p-8 max-w-3xl w-full max-h-[90vh] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
              >
                {modals.uploadModal.data}
              </motion.div>
            </motion.div>
          )}

          {/* Add Source Modal */}
          {modals.addSourceModal.isOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="fixed inset-0 bg-black/60 flex items-center justify-center z-[100] p-4"
              onClick={() => closeModal('addSourceModal')}
            >
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                transition={{ duration: 0.3 }}
                className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto scrollbar-hide shadow-2xl"
                onClick={(e) => e.stopPropagation()}
              >
                {modals.addSourceModal.data}
              </motion.div>
            </motion.div>
          )}



          {/* Gallery Settings Modal */}
          {modals.gallerySettings.isOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-[100] bg-black/60 flex items-center justify-center"
              onClick={() => closeModal('gallerySettings')}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                transition={{ type: "spring", duration: 0.3 }}
                className="bg-white rounded-lg shadow-lg w-96 p-6"
                onClick={(e) => e.stopPropagation()}
              >
                {modals.gallerySettings.data}
              </motion.div>
            </motion.div>
          )}

          {/* Customize Report Modal */}
          {modals.customizeReport.isOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-[100] bg-black/60 flex items-center justify-center p-4"
              onClick={() => closeModal('customizeReport')}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                transition={{ type: "spring", duration: 0.3 }}
                className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
              >
                {modals.customizeReport.data}
              </motion.div>
            </motion.div>
          )}

          {/* Customize Podcast Modal */}
          {modals.customizePodcast.isOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-[100] bg-black/60 flex items-center justify-center p-4"
              onClick={() => closeModal('customizePodcast')}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                transition={{ type: "spring", duration: 0.3 }}
                className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
              >
                {modals.customizePodcast.data}
              </motion.div>
            </motion.div>
          )}

          {/* Notebook Settings Modal */}
          {modals.notebookSettings.isOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-[100] bg-black/60 flex items-center justify-center p-4"
              onClick={() => closeModal('notebookSettings')}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                transition={{ type: "spring", duration: 0.3 }}
                className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden"
                onClick={(e) => e.stopPropagation()}
              >
                <NotebookSettingsModal
                  isOpen={true}
                  onClose={() => closeModal('notebookSettings')}
                  notebookId={notebookId}
                />
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        <Toaster />
      </div>
    </NotebookSettingsProvider>
  );
};

export default NotebookLayout;
