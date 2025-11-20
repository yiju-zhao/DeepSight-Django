import React, { useMemo } from 'react';
import { Podcast } from '../types/type';
import { PodcastService } from '../services/PodcastService';

interface PodcastListItemProps {
  podcast: Podcast;
}

const PodcastListItem: React.FC<PodcastListItemProps> = ({ podcast }) => {
  const podcastService = useMemo(() => new PodcastService(), []);

  // Generate preview text from description or topic
  const getPreviewText = () => {
    if (podcast.description) {
      return podcast.description.length > 100
        ? podcast.description.substring(0, 100) + '...'
        : podcast.description;
    }
    if (podcast.topic) {
      return podcast.topic.length > 100
        ? podcast.topic.substring(0, 100) + '...'
        : podcast.topic;
    }
    return '1. 什么是平衡短期和长期回报的最优策略? 在许多实际应用中,决策者需要同时考虑短期和长...';
  };

  return (
    <div className="mb-3">
      {/* Main item */}
      <div
        className="flex items-start space-x-3 bg-white border border-gray-200 p-3 rounded-xl transition"
      >
        {/* Neutral square icon with three lines */}
        <div className="w-8 h-8 bg-gray-100 border border-gray-200 rounded flex items-center justify-center flex-shrink-0">
          <div className="flex flex-col space-y-0.5">
            <div className="w-3 h-0.5 bg-gray-500 rounded"></div>
            <div className="w-3 h-0.5 bg-gray-500 rounded"></div>
            <div className="w-3 h-0.5 bg-gray-500 rounded"></div>
          </div>
        </div>

        <div className="flex-1 min-w-0">
          {/* Title */}
          <h3 className="text-base font-semibold text-gray-900 mb-1.5">
            {podcast.title || '新兴人工智能研究进展:从对齐到场景理解'}
          </h3>

          {/* Preview text */}
          <p className="text-sm text-gray-700 leading-relaxed">
            {getPreviewText()}
          </p>
        </div>
      </div>
    </div>
  );
};

export default PodcastListItem; 
