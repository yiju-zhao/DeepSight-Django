import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/shared/hooks/useAuth";
import { useNotebooks, useCreateNotebook, useDeleteNotebook } from "@/features/notebook/queries";
import NotebookGrid from "@/features/notebook/components/NotebookGrid";
import NotebookList from "@/features/notebook/components/NotebookList";
import CreateNotebookForm from "@/features/notebook/components/CreateNotebookForm";
import AppLayout from "@/shared/components/layout/AppLayout";
import MainPageHeader from "@/shared/components/common/MainPageHeader";
import {
  ChevronDown, Grid, List, Plus, BookOpen, Search, LogOut
} from "lucide-react";

/**
 * NotebookListPage component
 * Uses extracted hooks and smaller focused components
 */
export default function NotebookListPage() {
  const navigate = useNavigate();
  const { isAuthenticated, user, authChecked, handleLogout } = useAuth();
  const [sortOrder, setSortOrder] = useState("recent");
  const [searchTerm, setSearchTerm] = useState("");

  // Map UI sort order to API ordering parameter
  const ordering = sortOrder === 'recent' ? '-created_at' : 'created_at';

  const { data: notebooksResponse, isLoading: loading, error: listError } = useNotebooks({ ordering }, isAuthenticated && authChecked);
  const createMutation = useCreateNotebook();
  const deleteMutation = useDeleteNotebook();

  // UI state
  const [isGridView, setIsGridView] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [creating, setCreating] = useState(false);

  // No manual fetch; React Query handles caching and refetching

  // Handle notebook creation
  const handleCreateNotebook = async (name: string, description: string) => {
    if (!user) {
      return { success: false, error: "User not authenticated" };
    }

    setCreating(true);
    try {
      const newNotebook = await createMutation.mutateAsync({ name, description });
      if (newNotebook?.id) navigate(`/deepdive/${newNotebook.id}`);
      return { success: true };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      return { success: false, error: errorMessage };
    } finally {
      setCreating(false);
    }
  };

  // Handle notebook deletion
  const handleDeleteNotebook = async (notebookId: string) => {
    try {
      await deleteMutation.mutateAsync(notebookId);
    } catch (err) {
      console.error('Failed to delete notebook:', err);
    }
  };

  // Filter notebooks based on search term
  const notebooks = notebooksResponse?.data ?? [];
  const filteredNotebooks = notebooks.filter((notebook: any) =>
    notebook.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (notebook.description && notebook.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  // Format date helper
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.ceil(diffDays / 7)} weeks ago`;
    return date.toLocaleDateString();
  };

  // Show loading screen while checking authentication
  if (!authChecked) {
    return (
      <AppLayout showNavigation={false}>
        <div className="min-h-screen bg-white flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading...</p>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="min-h-screen bg-gray-50">
        <MainPageHeader
          title="DeepDive"
          subtitle="Manage your research"
          icon={<BookOpen className="w-5 h-5 text-white" />}
          iconColor="from-red-500 to-red-600"
        />

      {/* Main Content */}
      <main className="w-full px-4 sm:px-6 lg:px-8 py-8">
        {/* Top Section with Search and Actions */}
        <div className="mb-8">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0 mb-6">
            <div className="flex-1 max-w-md">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search notebooks..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-white border border-gray-300 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-transparent transition-all"
                />
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <button
                onClick={() => setShowCreateForm(!showCreateForm)}
                className="flex items-center space-x-2 px-4 py-3 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl hover:from-red-600 hover:to-red-700 transition-all shadow-lg hover:shadow-xl"
              >
                <Plus className="w-4 h-4" />
                <span className="font-medium">New Notebook</span>
              </button>
              
              <div className="flex items-center space-x-1 bg-white rounded-xl border border-gray-300 p-1">
                <button
                  onClick={() => setIsGridView(true)}
                  className={`p-2 rounded-lg transition-colors ${
                    isGridView 
                      ? "bg-red-100 text-red-600" 
                      : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
                  }`}
                >
                  <Grid className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setIsGridView(false)}
                  className={`p-2 rounded-lg transition-colors ${
                    !isGridView 
                      ? "bg-red-100 text-red-600" 
                      : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
                  }`}
                >
                  <List className="w-4 h-4" />
                </button>
              </div>
              
              <div className="relative">
                <select
                  value={sortOrder}
                  onChange={(e) => setSortOrder(e.target.value)}
                  className="appearance-none bg-white border border-gray-300 rounded-xl px-4 py-3 pr-10 focus:ring-2 focus:ring-red-500 focus:border-transparent transition-all"
                >
                  <option value="recent">Most Recent</option>
                  <option value="oldest">Oldest First</option>
                </select>
                <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
              </div>
            </div>
          </div>

          {/* Create Form */}
          {showCreateForm && (
            <CreateNotebookForm 
              onSubmit={handleCreateNotebook}
              onCancel={() => setShowCreateForm(false)}
              loading={creating}
              error={createMutation.isError ? (createMutation.error as Error).message : undefined}
            />
          )}
        </div>

        {/* Error Display */}
        {listError && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl">
            <p className="text-red-600 font-medium">{String(listError)}</p>
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="w-12 h-12 border-4 border-red-200 border-t-red-600 rounded-full animate-spin mb-4"></div>
            <p className="text-gray-600 font-medium">Loading your notebooks...</p>
          </div>
        ) : filteredNotebooks.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-red-100 to-red-200 rounded-2xl flex items-center justify-center">
              <BookOpen className="w-10 h-10 text-red-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              {searchTerm ? "No notebooks found" : "No notebooks yet"}
            </h2>
            <p className="text-gray-600 mb-8 max-w-md mx-auto">
              {searchTerm 
                ? `No notebooks match "${searchTerm}". Try a different search term.`
                : "Create your first notebook to start organizing your research and ideas."
              }
            </p>
            {!searchTerm && (
              <button
                onClick={() => setShowCreateForm(true)}
                className="inline-flex items-center space-x-2 px-8 py-4 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl hover:from-red-600 hover:to-red-700 transition-all shadow-lg hover:shadow-xl font-medium"
              >
                <Plus className="w-5 h-5" />
                <span>Create Your First Notebook</span>
              </button>
            )}
          </div>
        ) : isGridView ? (
          <NotebookGrid 
            notebooks={filteredNotebooks}
            onNotebookClick={(notebook) => navigate(`/deepdive/${notebook.id}`)}
            onDeleteNotebook={handleDeleteNotebook}
            formatDate={formatDate}
          />
        ) : (
          <NotebookList 
            notebooks={filteredNotebooks}
            onNotebookClick={(notebook) => navigate(`/deepdive/${notebook.id}`)}
            onDeleteNotebook={handleDeleteNotebook}
            formatDate={formatDate}
          />
        )}
      </main>
      </div>
    </AppLayout>
  );
}
