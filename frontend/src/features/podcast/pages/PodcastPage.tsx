import React, { useEffect, useState, useMemo } from 'react';
import {
  usePodcasts,
  usePodcast,
  usePodcastStats,
  useDeletePodcast,
  useCancelPodcast,
} from '@/features/podcast/hooks/usePodcasts';
import { PodcastService } from '@/features/podcast/services/PodcastService';
import PodcastList from "@/features/podcast/components/PodcastList";
import PodcastFilters from "@/features/podcast/components/PodcastFilters";

import PodcastDetail from "@/features/podcast/components/PodcastDetail";
import { Podcast, PodcastFilters as PodcastFiltersType } from "@/features/podcast/types/type";
import { config } from "@/config";
import { useToast } from "@/shared/components/ui/use-toast";
import Header from '@/shared/components/layout/Header';
import { Mic, Sparkles } from 'lucide-react';

const PodcastPage: React.FC = () => {
  // UI state (local)
  const [searchTerm, setSearchTerm] = useState('');
  const [sortOrder, setSortOrder] = useState<'recent' | 'oldest' | 'title'>('recent');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [filters, setFilters] = useState<PodcastFiltersType>({});
  const [selectedPodcast, setSelectedPodcast] = useState<Podcast | null>(null);
  const [showDetail, setShowDetail] = useState(false);

  // Server state (TanStack Query)
  const { data: podcasts = [], isLoading, error } = usePodcasts(undefined, filters);
  const { data: stats } = usePodcastStats();
  const deletePodcastMutation = useDeletePodcast();
  const cancelPodcastMutation = useCancelPodcast();
  const { toast } = useToast();

  // Service for client-side filtering and sorting
  const podcastService = useMemo(() => new PodcastService(), []);

  // Derived data: filtered and sorted podcasts
  const processedPodcasts = useMemo(() => {
    let result = [...podcasts];

    // Apply search filter
    if (searchTerm) {
      result = podcastService.filterPodcasts(result, { ...filters, search: searchTerm });
    }

    // Apply sorting
    result = podcastService.sortPodcasts(result, sortOrder);

    return result;
  }, [podcasts, searchTerm, filters, sortOrder, podcastService]);

  // Fetch detailed podcast data when selecting a completed podcast
  const { data: detailedPodcast, refetch: refetchPodcast } = usePodcast(
    selectedPodcast?.id || ''
  );

  useEffect(() => {
    if (selectedPodcast && selectedPodcast.status === 'completed') {
      refetchPodcast();
    }
  }, [selectedPodcast, refetchPodcast]);

  // Use detailed podcast if available, fallback to selected
  const displayPodcast = detailedPodcast || selectedPodcast;

  const handleSelectPodcast = async (podcast: Podcast) => {
    setSelectedPodcast(podcast);
    setShowDetail(true);
  };

  const handleBackToList = () => {
    setShowDetail(false);
    setSelectedPodcast(null);
  };

  const handleSearchChange = (term: string) => {
    setSearchTerm(term);
  };

  const handleSortChange = (order: 'recent' | 'oldest' | 'title') => {
    setSortOrder(order);
  };

  const handleViewModeChange = (mode: 'grid' | 'list') => {
    setViewMode(mode);
  };

  const handleFiltersChange = (newFilters: PodcastFiltersType) => {
    setFilters(newFilters);
  };

  const handleDownloadPodcast = async (podcast: Podcast) => {
    if (!podcast.notebook_id) {
      console.error('No notebook ID found for podcast');
      return;
    }

    try {
      // Directly navigate to the download endpoint, let browser handle the download
      const downloadUrl = `${config.API_BASE_URL}/podcasts/${podcast.id}/audio/?download=1`;
      window.open(downloadUrl, '_blank');
    } catch (error) {
      console.error('Failed to download podcast:', error);
    }
  };

  const handleDeletePodcast = async (podcast: Podcast) => {
    // Replicate report deletion flow: attempt delete;
    // backend will reject running jobs with 400 instructing to cancel first.
    const confirmMessage = 'Are you sure you want to delete this podcast?';
    if (!confirm(confirmMessage)) return;
    try {
      await deletePodcastMutation.mutateAsync(podcast.id);
      toast({ title: 'Podcast Deleted', description: 'Deleted successfully' });
    } catch (error) {
      console.error('Failed to delete podcast:', error);
      const message = error instanceof Error ? error.message : 'Failed to delete podcast';
      toast({ title: 'Delete Failed', description: message, variant: 'destructive' });
    }
  };

  const handlePlayPodcast = (podcast: Podcast) => {
    // This would be implemented with audio playback
    console.log('Playing podcast:', podcast.id);
  };

  const handleEditPodcast = (podcast: Podcast) => {
    // This would navigate to edit mode
    console.log('Editing podcast:', podcast.id);
  };

  if (showDetail && displayPodcast) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Header />
        <main className="flex-grow pt-[var(--header-height)]">
          <PodcastDetail
            podcast={displayPodcast}
            isLoading={isLoading}
            onDownload={handleDownloadPodcast}
            onDelete={handleDeletePodcast}
            onPlay={handlePlayPodcast}
            onEdit={handleEditPodcast}
            onBack={handleBackToList}
          />
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      <main className="flex-grow pt-[var(--header-height)]">
        {/* Modern Page Header */}
        <section className="relative bg-white border-b border-gray-100">
          <div className="absolute inset-0 bg-gradient-to-b from-gray-50/50 to-white/20 pointer-events-none" />
          <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-6 relative z-10">
            <div className="max-w-3xl">
              <div className="flex items-center gap-2 mb-4">
                <span className="px-3 py-1 rounded-full bg-purple-50 text-xs font-medium text-purple-600 flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  Audio
                </span>
              </div>
              <h1 className="text-4xl font-bold text-[#1E1E1E] tracking-tight mb-4">
                AI Podcasts
              </h1>
              <p className="text-lg text-gray-500 leading-relaxed">
                Generate and manage your AI-powered podcast discussions.
              </p>
            </div>
          </div>
        </section>

        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {/* Filters and Controls */}
          <div className="mb-8 bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <PodcastFilters
              filters={filters}
              onFiltersChange={handleFiltersChange}
            />

            {/* Search and View Controls */}
            <div className="mt-6 pt-6 border-t border-gray-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="flex-1 max-w-md">
                <input
                  type="text"
                  placeholder="Search podcasts..."
                  value={searchTerm}
                  onChange={(e) => handleSearchChange(e.target.value)}
                  className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-black/5 focus:border-black/20 transition-all"
                />
              </div>

              <div className="flex items-center gap-4">
                {/* Sort Order */}
                <select
                  value={sortOrder}
                  onChange={(e) => handleSortChange(e.target.value as 'recent' | 'oldest' | 'title')}
                  className="px-4 py-2.5 bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-black/5 focus:border-black/20 transition-all text-sm font-medium text-gray-700"
                >
                  <option value="recent">Most Recent</option>
                  <option value="oldest">Oldest First</option>
                  <option value="title">Title A-Z</option>
                </select>

                {/* View Mode */}
                <div className="flex bg-gray-100 p-1 rounded-lg">
                  <button
                    onClick={() => handleViewModeChange('grid')}
                    className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${viewMode === 'grid'
                      ? 'bg-white text-black shadow-sm'
                      : 'text-gray-500 hover:text-gray-900'
                      }`}
                  >
                    Grid
                  </button>
                  <button
                    onClick={() => handleViewModeChange('list')}
                    className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${viewMode === 'list'
                      ? 'bg-white text-black shadow-sm'
                      : 'text-gray-500 hover:text-gray-900'
                      }`}
                  >
                    List
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="mb-8 bg-red-50 border border-red-100 rounded-xl p-4 flex items-center gap-3">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <p className="text-sm text-red-800 font-medium">
                {error instanceof Error ? error.message : 'An error occurred while loading podcasts'}
              </p>
            </div>
          )}

          {/* Podcasts List */}
          <div className="bg-transparent">
            <PodcastList
              podcasts={processedPodcasts}
              isLoading={isLoading}
              onSelectPodcast={handleSelectPodcast}
              onDownloadPodcast={handleDownloadPodcast}
              onDeletePodcast={handleDeletePodcast}
              onPlayPodcast={handlePlayPodcast}
              onEditPodcast={handleEditPodcast}
              selectedPodcastId={selectedPodcast?.id}
              viewMode={viewMode}
            />
          </div>

          {/* Empty State */}
          {!isLoading && processedPodcasts.length === 0 && (
            <div className="flex flex-col items-center justify-center py-24 bg-white rounded-2xl border border-dashed border-gray-200">
              <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mb-4">
                <Mic className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No podcasts found</h3>
              <p className="text-gray-500 text-center max-w-sm">
                {searchTerm || Object.keys(filters).length > 0
                  ? 'Try adjusting your search or filters to find what you are looking for.'
                  : 'Get started by creating your first AI podcast discussion.'
                }
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default PodcastPage;
