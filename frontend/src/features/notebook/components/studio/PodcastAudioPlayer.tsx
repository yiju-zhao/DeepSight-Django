// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Simple podcast item with native audio player

import React, { useState, useEffect } from 'react';
import {
  Download,
  Trash2,
  Loader2
} from 'lucide-react';
import { Button } from "@/shared/components/ui/button";
import { PodcastService } from "@/features/podcast/services/PodcastService";
import type { Podcast } from "@/features/podcast/types/type";
import { config } from "@/config";

interface PodcastAudioPlayerProps {
  podcast: Podcast;
  onDownload: (podcast: Podcast) => void;
  onDelete: (podcast: Podcast) => void;
  notebookId?: string;
}

const PodcastAudioPlayer: React.FC<PodcastAudioPlayerProps> = ({
  podcast,
  onDownload,
  onDelete,
  notebookId
}) => {
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [currentPodcast, setCurrentPodcast] = useState<Podcast>(podcast);

  const formatDate = (dateString?: string): string => {
    if (!dateString) return '';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return '';
    }
  };

  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return '';
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Update current podcast when prop changes
  useEffect(() => {
    setCurrentPodcast(podcast);
  }, [podcast]);

  // Set audio URL - let browser handle fetching and redirects directly
  useEffect(() => {
    // Check if podcast is completed and has audio_object_key
    if (!currentPodcast.id) {
      console.log('No podcast ID available');
      setAudioUrl(null);
      setIsLoading(false);
      return;
    }

    if (currentPodcast.status !== 'completed') {
      console.log(`Podcast status is '${currentPodcast.status}', not 'completed'`);
      setAudioUrl(null);
      setIsLoading(false);
      return;
    }

    if (!(currentPodcast as any).audio_object_key) {
      console.log('Podcast has no audio_object_key');
      setAudioUrl(null);
      setIsLoading(false);
      return;
    }

    // Use endpoint URL directly - browser will handle auth and redirects
    const audioEndpoint = `${config.API_BASE_URL}/podcasts/${currentPodcast.id}/audio/`;
    console.log(`Setting audio URL: ${audioEndpoint}`);
    setAudioUrl(audioEndpoint);
    setIsLoading(false);
  }, [currentPodcast.id, currentPodcast.status]);

  return (
    <div className="p-4 border border-gray-200 rounded-lg bg-white">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-gray-900 truncate">
            {currentPodcast.title || 'Untitled Panel Discussion'}
          </h4>
          <div className="flex items-center space-x-3 text-xs text-gray-500 mt-1">
            <span>{formatDate(currentPodcast.created_at)}</span>
            {(currentPodcast as any).file_size && (
              <>
                <span>•</span>
                <span>{formatFileSize((currentPodcast as any).file_size)}</span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDownload(currentPodcast)}
            className="h-8 w-8 p-0 text-gray-500 hover:text-gray-700"
            title="Download audio"
          >
            <Download className="h-4 w-4" />
          </Button>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(currentPodcast)}
            className="h-8 w-8 p-0 text-gray-500 hover:text-red-600"
            title="Delete podcast"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Audio Player */}
      {isLoading ? (
        <div className="flex items-center justify-center py-2 text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin mr-2" />
          <span className="text-sm">Loading audio...</span>
        </div>
      ) : audioUrl ? (
        <audio
          controls
          className="w-full"
          preload="metadata"
          style={{ height: '40px' }}
          src={audioUrl}
        >
          Your browser does not support the audio element.
        </audio>
      ) : (
        <div className="text-center py-2 text-gray-500 text-sm">
          {currentPodcast.status !== 'completed'
            ? `Podcast ${currentPodcast.status}...`
            : !(currentPodcast as any).audio_object_key
            ? 'Audio file not found'
            : 'Audio not available'}
        </div>
      )}
    </div>
  );
};

export default React.memo(PodcastAudioPlayer);
