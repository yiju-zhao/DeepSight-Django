/**
 * Podcasts section component for the dashboard
 * Handles display of podcasts
 */

import React from 'react';
import PodcastListItem from '@/features/podcast/components/PodcastListItem';
import { Podcast } from '../queries';

interface PodcastsSectionProps {
  podcasts: Podcast[];
  onPodcastSelect: (podcast: Podcast) => void;
  loading?: boolean;
  className?: string;
}

const PodcastsSection: React.FC<PodcastsSectionProps> = ({
  podcasts,
  onPodcastSelect,
  loading = false,
  className = '',
}) => {
  if (loading) {
    return (
      <div className={`mb-8 ${className}`}>
        <div className="bg-white/80 backdrop-blur-sm rounded-xl border border-gray-200 shadow-sm p-6">
          <div className="space-y-4">
            {[1, 2].map(i => (
              <div key={i} className="animate-pulse">
                <div className="h-20 bg-gray-200 rounded-lg"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (podcasts.length === 0) {
    return (
      <div className={`mb-8 ${className}`}>
        <div className="bg-white/80 backdrop-blur-sm rounded-xl border border-gray-200 shadow-sm p-6">
          <div className="text-center py-6">
            <div className="h-10 w-10 rounded-full border border-dashed border-gray-300 mx-auto mb-3 flex items-center justify-center text-gray-400">🎧</div>
            <h3 className="text-sm font-medium text-gray-900 mb-1">No podcasts yet</h3>
            <p className="text-xs text-gray-500">Create your first AI-generated podcast.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`h-full ${className}`}>
      <div className="bg-white/80 backdrop-blur-sm rounded-xl border border-gray-200 shadow-sm h-full flex flex-col">
        <div className="p-6 pb-4 flex-shrink-0">
          <h2 className="text-base font-semibold text-gray-900">Latest Podcasts</h2>
          <p className="text-xs text-gray-500">Fresh AI-generated audio content</p>
        </div>
        <div className="flex-1 px-6 pb-6 overflow-y-auto min-h-0">
          <div className="space-y-3">
            {podcasts.map((podcast) => (
              <PodcastListItem
                key={podcast.id}
                podcast={podcast}
                onSelect={onPodcastSelect}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PodcastsSection;
