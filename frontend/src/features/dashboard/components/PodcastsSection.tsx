/**
 * Podcasts section component for the dashboard
 * Handles display of latest podcasts with modern Huawei-style design
 * Optimized with React.memo to prevent unnecessary re-renders
 */

import React, { useMemo } from 'react';
import PodcastListItem from '@/features/podcast/components/PodcastListItem';
import { Card } from '@/shared/components/ui/card';
import { SectionHeader } from '@/shared/components/ui/section-header';
import { Button } from '@/shared/components/ui/button';
import { Headphones } from 'lucide-react';
import { Podcast } from '../queries';

interface PodcastsSectionProps {
  podcasts: Podcast[];
  onPodcastSelect: (podcast: Podcast) => void;
  onViewAll?: () => void;
  loading?: boolean;
  className?: string;
}

const PodcastsSection: React.FC<PodcastsSectionProps> = React.memo(({
  podcasts,
  onPodcastSelect,
  onViewAll,
  loading = false,
  className = '',
}) => {
  // Limit to 3 podcasts for dashboard
  const displayPodcasts = useMemo(() => podcasts.slice(0, 3), [podcasts]);

  // Memoize loading skeleton
  const loadingSkeleton = useMemo(() => (
    <Card variant="elevated" className={className}>
      <div className="p-6 space-y-4">
        <div className="h-6 bg-gray-200 rounded animate-pulse w-48" />
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-20 bg-gray-200 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    </Card>
  ), [className]);

  if (loading) {
    return loadingSkeleton;
  }

  if (podcasts.length === 0) {
    return (
      <Card variant="elevated" className={className}>
        <div className="p-6">
          <SectionHeader title="Latest Podcasts" />
          <div className="text-center py-8">
            <Headphones className="h-12 w-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-sm font-medium text-gray-900 mb-1">No podcasts yet</h3>
            <p className="text-xs text-gray-500">Create your first AI-generated podcast.</p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card variant="elevated" hoverable className={className}>
      <div className="p-6">
        <SectionHeader
          title="Latest Podcasts"
          action={
            onViewAll && podcasts.length > 3 && (
              <Button variant="ghost" size="sm" withArrow onClick={onViewAll}>
                View All
              </Button>
            )
          }
        />

        <div className="space-y-3">
          {displayPodcasts.map((podcast) => (
            <PodcastListItem
              key={podcast.id}
              podcast={podcast}
              onSelect={onPodcastSelect}
            />
          ))}
        </div>

        {onViewAll && podcasts.length > 3 && (
          <div className="mt-6 pt-4 border-t border-border">
            <Button variant="accent" withArrow onClick={onViewAll} className="w-full md:w-auto">
              View All Podcasts
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
});

PodcastsSection.displayName = 'PodcastsSection';

export default PodcastsSection;
