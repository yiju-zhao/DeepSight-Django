/**
 * Delete Confirmation Context
 * Handles delete confirmation modal state without storing callbacks in Redux
 */

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';

interface DeleteConfirmationState {
  isOpen: boolean;
  title?: string;
  message?: string;
  onConfirm?: () => void;
}

interface DeleteConfirmationContextType {
  state: DeleteConfirmationState;
  open: (options: { title: string; message: string; onConfirm: () => void }) => void;
  close: () => void;
}

const DeleteConfirmationContext = createContext<DeleteConfirmationContextType | undefined>(undefined);

export const DeleteConfirmationProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, setState] = useState<DeleteConfirmationState>({
    isOpen: false,
  });

  const open = useCallback((options: { title: string; message: string; onConfirm: () => void }) => {
    setState({
      isOpen: true,
      ...options,
    });
  }, []);

  const close = useCallback(() => {
    setState({
      isOpen: false,
      title: undefined,
      message: undefined,
      onConfirm: undefined,
    });
  }, []);

  return (
    <DeleteConfirmationContext.Provider value={{ state, open, close }}>
      {children}
    </DeleteConfirmationContext.Provider>
  );
};

export const useDeleteConfirmation = () => {
  const context = useContext(DeleteConfirmationContext);
  if (!context) {
    throw new Error('useDeleteConfirmation must be used within DeleteConfirmationProvider');
  }
  return context;
};
