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
        <div className="space-y-4">
          {[1, 2].map(i => (
            <div key={i} className="animate-pulse">
              <div className="h-20 bg-gray-200 rounded-lg"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (podcasts.length === 0) {
    return (
      <div className={`mb-8 ${className}`}>
        <div className="text-center py-8">
          <div className="text-gray-400 text-4xl mb-2">🎧</div>
          <h3 className="text-lg font-medium text-gray-900 mb-1">No podcasts yet</h3>
          <p className="text-sm text-gray-500">
            Start by creating your first AI-generated podcast.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`mb-8 ${className}`}>
      <h2 className="text-2xl font-semibold mb-4 text-gray-900">Latest Podcasts</h2>
      <div className="space-y-4">
        {podcasts.map((podcast) => (
          <PodcastListItem
            key={podcast.id}
            podcast={podcast}
            onSelect={onPodcastSelect}
          />
        ))}
      </div>
    </div>
  );
};

export default PodcastsSection;