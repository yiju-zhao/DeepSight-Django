/**
 * 
 * Modern Notebook Grid Component using new architecture
 */

import React, { useMemo, useState, Suspense } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, Grid, List, Trash2, X } from 'lucide-react';
import { useNotebooks, useCreateNotebook, useDeleteNotebook } from "@/features/notebook/hooks/api";
import { ErrorBoundary } from "@/shared/components/ui/ErrorBoundary";
import { LoadingSpinner, NotebookGridSkeleton } from "@/shared/components/ui/LoadingSpinner";
import { Button } from "@/shared/components/ui/button";
import { DataTable } from "@/shared/components/ui/DataTable";
import { useDeferredSearch, useSmartLoading } from "@/shared/hooks/useConcurrentFeatures";
import CreateNotebookForm from "@/features/notebook/components/CreateNotebookForm";
import type { ColumnDef } from '@tanstack/react-table';
import type { Notebook } from "@/shared/api";
import { cn } from "@/shared/utils/utils";
import { motion, AnimatePresence } from "framer-motion";

interface NotebookGridProps {
  className?: string;
}

export const NotebookGrid: React.FC<NotebookGridProps> = ({ className }) => {
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [notebookToDelete, setNotebookToDelete] = useState<Notebook | null>(null);

  // Use React 18 concurrent features for search
  const {
    query: searchQuery,
    deferredQuery,
    isPending: isSearchPending,
    updateQuery: handleSearchChange,
    clearQuery: clearSearch,
    isStale: isSearchStale,
  } = useDeferredSearch();

  // Queries with deferred search
  const {
    data: notebooksResponse,
    isLoading,
    error,
    refetch,
  } = useNotebooks({
    search: deferredQuery, // Use deferred query for server requests
    ordering: '-updated_at',
  });

  // Smart loading to prevent flickering
  const { shouldShowLoading } = useSmartLoading(isLoading, 300);

  const createNotebook = useCreateNotebook();
  const deleteNotebook = useDeleteNotebook();

  // Memoized notebooks data
  const notebooks = useMemo(() => {
    if (!notebooksResponse) return [];
    return Array.isArray(notebooksResponse) ? notebooksResponse : (notebooksResponse as any)?.results || [];
  }, [notebooksResponse]);

  // Handle create notebook submission
  const handleCreateNotebook = async (name: string, description: string) => {
    try {
      const newNotebook = await createNotebook.mutateAsync({
        name,
        description,
      }) as Notebook;
      setShowCreateForm(false);
      navigate(`/deepdive/${newNotebook.id}`);
      return { success: true };
    } catch (error) {
      console.error('Failed to create notebook:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to create notebook'
      };
    }
  };

  // Handle notebook click
  const handleNotebookClick = (notebook: Notebook) => {
    navigate(`/deepdive/${notebook.id}`);
  };

  // Handle delete notebook
  const handleDeleteNotebook = async () => {
    if (!notebookToDelete) return;

    try {
      await deleteNotebook.mutateAsync(notebookToDelete.id);
      setNotebookToDelete(null);
    } catch (error) {
      console.error('Failed to delete notebook:', error);
    }
  };

  // Table columns definition
  const columns = useMemo<ColumnDef<Notebook>[]>(() => [
    {
      accessorKey: 'name',
      header: 'Name',
      cell: ({ row }) => (
        <span className="font-medium text-gray-900">{row.original.name}</span>
      ),
    },
    {
      accessorKey: 'source_count',
      header: 'Sources',
      cell: ({ row }) => (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
          {row.original.source_count} sources
        </span>
      ),
    },
    {
      accessorKey: 'updated_at',
      header: 'Last Updated',
      cell: ({ row }) => (
        <span className="text-sm text-gray-500">
          {new Date(row.original.updated_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            setNotebookToDelete(row.original);
          }}
          className="text-red-600 hover:text-red-800 transition-colors p-2"
          title="Delete notebook"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      ),
    },
  ], []);

  // Grid view component
  const GridView: React.FC = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {notebooks.map((notebook: Notebook) => (
        <div
          key={notebook.id}
          className="group bg-white rounded-2xl shadow-md hover:shadow-xl transition-all duration-300 cursor-pointer relative"
          onClick={() => handleNotebookClick(notebook)}
        >
          <div className="p-6">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h3 className="text-lg font-semibold text-gray-900 truncate group-hover:text-accent-red transition-colors">
                  {notebook.name}
                </h3>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setNotebookToDelete(notebook);
                }}
                className="text-gray-400 hover:text-accent-red transition-colors p-1 rounded hover:bg-accent-red-subtle"
                title="Delete notebook"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>

            <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
              <div className="flex items-center space-x-4">
                <span>{notebook.source_count} sources</span>
              </div>
              <span>
                {new Date(notebook.updated_at).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );

  if (error) {
    return (
      <div className="text-center py-16 bg-white rounded-lg shadow-huawei-sm border border-border">
        <p className="text-accent-red mb-4 font-medium">Failed to load notebooks</p>
        <Button onClick={() => refetch()} variant="outline" className="border-border">
          Try Again
        </Button>
      </div>
    );
  }

  return (
    <ErrorBoundary level="section">
      <div className={cn('space-y-6', className)}>

        {/* Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="relative max-w-md w-full">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search notebooks..."
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              className={cn(
                "w-full pl-10 pr-4 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent transition-all text-sm shadow-sm",
                isSearchStale && "bg-yellow-50"
              )}
            />
            {(isSearchPending || isSearchStale) && (
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                <LoadingSpinner size="sm" />
              </div>
            )}
          </div>

          <div className="flex items-center space-x-3">
            {/* New Notebook Button */}
            <Button
              onClick={() => setShowCreateForm(true)}
              disabled={createNotebook.isPending}
              className="inline-flex items-center bg-accent-red hover:bg-accent-red-hover"
            >
              <Plus className="w-4 h-4 mr-2" />
              New Notebook
            </Button>

            {/* View Toggle */}
            <div className="flex items-center rounded-lg p-1 bg-white shadow-sm">
              <Button
                variant={viewMode === 'grid' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('grid')}
                className={cn(
                  "rounded-md",
                  viewMode === 'grid'
                    ? "bg-accent-red text-white hover:bg-accent-red-hover"
                    : "text-muted-foreground"
                )}
              >
                <Grid className="w-4 h-4" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('list')}
                className={cn(
                  "rounded-md",
                  viewMode === 'list'
                    ? "bg-accent-red text-white hover:bg-accent-red-hover"
                    : "text-muted-foreground"
                )}
              >
                <List className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Loading State with smart loading */}
        {shouldShowLoading && (
          <NotebookGridSkeleton count={8} />
        )}

        {/* Content */}
        {!shouldShowLoading && (
          <Suspense fallback={<NotebookGridSkeleton count={8} />}>
            {notebooks.length === 0 ? (
              <div className="text-center py-12">
                <div className="max-w-md mx-auto">
                  <div className="w-12 h-12 mx-auto mb-4 text-gray-400">
                    <Plus className="w-full h-full" />
                  </div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    No notebooks yet
                  </h3>
                  <p className="text-gray-500 mb-6">
                    Get started by creating your first notebook to organize your research and knowledge.
                  </p>
                  <Button onClick={() => setShowCreateForm(true)}>
                    <Plus className="w-4 h-4 mr-2" />
                    Create Your First Notebook
                  </Button>
                </div>
              </div>
            ) : viewMode === 'grid' ? (
              <GridView />
            ) : (
              <DataTable
                columns={columns}
                data={notebooks}
                loading={isLoading}
                error={error}
                onRowClick={handleNotebookClick}
                globalFilter={searchQuery}
                onGlobalFilterChange={handleSearchChange}
                emptyMessage="No notebooks found"
                className="mt-6"
              />
            )}
          </Suspense>
        )}

        {/* Create Notebook Modal */}
        <AnimatePresence>
          {showCreateForm && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
              onClick={() => setShowCreateForm(false)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                transition={{ type: "spring", duration: 0.3 }}
                className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl"
                onClick={(e) => e.stopPropagation()}
              >
                {/* Modal Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                  <h3 className="text-lg font-semibold text-gray-900">Create New Notebook</h3>
                  <button
                    onClick={() => setShowCreateForm(false)}
                    className="p-2 rounded-lg hover:bg-secondary transition-colors"
                  >
                    <X className="w-5 h-5 text-muted-foreground" />
                  </button>
                </div>

                {/* Modal Content */}
                <div className="px-6 py-6">
                  <CreateNotebookForm
                    onSubmit={handleCreateNotebook}
                    onCancel={() => setShowCreateForm(false)}
                    loading={createNotebook.isPending}
                    error={createNotebook.error?.message}
                  />
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Delete Confirmation Dialog */}
        {notebookToDelete && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <div className="flex items-start mb-4">
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                  <Trash2 className="w-5 h-5 text-red-600" />
                </div>
                <div className="ml-4 flex-1">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Delete Notebook
                  </h3>
                  <p className="mt-2 text-sm text-gray-600">
                    Are you sure you want to delete "<span className="font-medium">{notebookToDelete.name}</span>"?
                    This action cannot be undone and will permanently delete all sources, knowledge items, and chat history.
                  </p>
                </div>
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <Button
                  variant="outline"
                  onClick={() => setNotebookToDelete(null)}
                  disabled={deleteNotebook.isPending}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleDeleteNotebook}
                  disabled={deleteNotebook.isPending}
                  className="bg-red-600 hover:bg-red-700 text-white"
                >
                  {deleteNotebook.isPending ? (
                    <>
                      <LoadingSpinner size="sm" color="white" className="mr-2" />
                      Deleting...
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-4 h-4 mr-2" />
                      Delete Notebook
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
};
