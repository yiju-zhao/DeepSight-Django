/**
 * TanStack Query Provider setup
 */

import React from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { queryClient } from '../queries/client';

interface QueryProviderProps {
  children: React.ReactNode;
}

export const QueryProvider: React.FC<QueryProviderProps> = ({ children }) => {
  const showDevtools = import.meta.env.DEV && import.meta.env.VITE_SHOW_RQ_DEVTOOLS === 'true';
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {showDevtools && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
};
