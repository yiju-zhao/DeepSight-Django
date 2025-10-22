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
  const [isLoading, setIsLoading] = useState(false);
  const [retryAttempts, setRetryAttempts] = useState(0);
  const [currentPodcast, setCurrentPodcast] = useState<Podcast>(podcast);
  const audioMime = React.useMemo(() => {
    const lower = (audioUrl || '').toLowerCase();
    if (!lower) return undefined;
    if (lower.includes('.wav')) return 'audio/wav';
    if (lower.includes('.mp3')) return 'audio/mpeg';
    return undefined;
  }, [audioUrl]);

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
    setRetryAttempts(0); // Reset retry attempts when podcast changes
  }, [podcast]);

  // Load audio URL with retry logic - fetch as blob to avoid CORS issues
  useEffect(() => {
    const loadAudio = async () => {
      setIsLoading(true);

      try {
        if (!currentPodcast.id) {
          console.log('No podcast ID available');
          setAudioUrl(null);
          return;
        }

        // Fetch audio as blob to handle MinIO redirect properly
        const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const audioEndpoint = `${apiBaseUrl}/podcasts/${currentPodcast.id}/audio/`;

        const response = await fetch(audioEndpoint, {
          method: 'GET',
          credentials: 'include',
          redirect: 'manual'
        });

        // Handle redirect to MinIO
        if (response.status === 302 || response.status === 301) {
          const redirectUrl = response.headers.get('Location');
          if (redirectUrl) {
            // Fetch from MinIO without credentials to avoid CORS issues
            const minioResponse = await fetch(redirectUrl, {
              method: 'GET',
              credentials: 'omit',
              mode: 'cors'
            });

            if (minioResponse.ok) {
              const blob = await minioResponse.blob();
              const blobUrl = URL.createObjectURL(blob);
              setAudioUrl(blobUrl);
              return;
            } else {
              throw new Error(`MinIO audio fetch failed: ${minioResponse.status}`);
            }
          }
        }

        // Direct response (no redirect)
        if (response.ok) {
          const blob = await response.blob();
          const blobUrl = URL.createObjectURL(blob);
          setAudioUrl(blobUrl);
          return;
        }

        throw new Error(`Audio fetch failed: ${response.status}`);
      } catch (error) {
        console.error('Error loading audio:', error);

        // Retry with exponential backoff if we haven't exceeded max attempts
        if (retryAttempts < 5) {
          const delay = Math.min(1000 * Math.pow(2, retryAttempts), 10000); // Max 10 seconds
          console.log(`Retrying audio load in ${delay}ms (attempt ${retryAttempts + 1}/5)`);
          setTimeout(() => {
            setRetryAttempts(prev => prev + 1);
          }, delay);
        } else {
          setAudioUrl(null);
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadAudio();

    // Cleanup: revoke blob URL when component unmounts or podcast changes
    return () => {
      if (audioUrl && audioUrl.startsWith('blob:')) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [currentPodcast.id, notebookId, retryAttempts]);

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
          <span className="text-sm">
            {retryAttempts > 0 ? `Retrying audio load... (${retryAttempts}/5)` : 'Loading audio...'}
          </span>
        </div>
      ) : audioUrl ? (
        <audio 
          controls 
          className="w-full"
          preload="metadata"
          style={{ height: '40px' }}
        >
          {audioMime ? <source src={audioUrl} type={audioMime} /> : <source src={audioUrl} />}
          Your browser does not support the audio element.
        </audio>
      ) : (
        <div className="text-center py-2 text-gray-500 text-sm">
          {retryAttempts >= 5 ? 'Audio not available after retries' : 'Audio not available'}
        </div>
      )}
    </div>
  );
};

export default React.memo(PodcastAudioPlayer);
