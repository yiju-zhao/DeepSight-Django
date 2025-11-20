import React, { useEffect, useState } from 'react';
import { Podcast, PodcastDetailProps } from '../types/type';
import { PodcastService } from '../services/PodcastService';
import { useNotebookJobStream } from '@/shared/hooks/useNotebookJobStream';
import { queryKeys } from '@/shared/queries/keys';
import { useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Download,
  Edit,
  Trash2,
  Calendar,
  Clock,
  Tag,
  Mic,
  Globe,
  Play,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Loader2,
  HelpCircle,
  FileText
} from 'lucide-react';
import { Button } from "@/shared/components/ui/button";

const PodcastDetail: React.FC<PodcastDetailProps> = ({
  podcast,
  isLoading,
  onDownload,
  onDelete,
  onPlay,
  onEdit,
  onBack
}) => {
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [currentPodcast, setCurrentPodcast] = useState<Podcast>(podcast);
  const queryClient = useQueryClient();

  // Update current podcast when prop changes
  useEffect(() => {
    setCurrentPodcast(podcast);
  }, [podcast]);

  // Use SSE for real-time updates
  useNotebookJobStream({
    notebookId: currentPodcast.notebook_id,
    enabled: !!(currentPodcast.notebook_id && (currentPodcast.status === 'generating' || currentPodcast.status === 'pending')),
    onConnected: () => {
      // Sync current state when SSE reconnects (e.g., after page refresh)
      console.log('[PodcastDetail] SSE connected, syncing podcast state');
      queryClient.invalidateQueries({ queryKey: queryKeys.podcasts.detail(currentPodcast.id) });
    },
    onJobEvent: (event) => {
      // Invalidate and refetch if this is our podcast
      if (event.entity === 'podcast' && event.id === currentPodcast.id) {
        queryClient.invalidateQueries({ queryKey: queryKeys.podcasts.detail(currentPodcast.id) });
      }
    },
  });

  // Set audio URL from podcast object
  useEffect(() => {
    if (currentPodcast.status === 'completed' && currentPodcast.audio_url) {
      const podcastService = new PodcastService();
      const url = podcastService.getAudioUrl(currentPodcast);
      setAudioUrl(url);
    } else {
      setAudioUrl(null);
    }
  }, [currentPodcast.status, currentPodcast.audio_url]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '—';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'completed': return { color: 'text-emerald-600 bg-emerald-50', icon: CheckCircle2 };
      case 'failed': return { color: 'text-red-600 bg-red-50', icon: XCircle };
      case 'generating': return { color: 'text-blue-600 bg-blue-50', icon: Loader2 };
      case 'pending': return { color: 'text-amber-600 bg-amber-50', icon: Clock };
      case 'cancelled': return { color: 'text-gray-600 bg-gray-50', icon: AlertCircle };
      default: return { color: 'text-gray-600 bg-gray-50', icon: HelpCircle };
    }
  };

  const statusConfig = getStatusConfig(currentPodcast.status);
  const StatusIcon = statusConfig.icon;

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-[1000px] mx-auto px-6 py-8">
        {/* Back Navigation */}
        <div className="mb-6">
          <button
            onClick={onBack}
            className="flex items-center text-sm text-gray-500 hover:text-gray-900 transition-colors group"
          >
            <ArrowLeft className="w-4 h-4 mr-1 group-hover:-translate-x-1 transition-transform" />
            Back to Podcasts
          </button>
        </div>

        {/* Header Section */}
        <div className="mb-8 border-b border-gray-100 pb-8">
          <div className="flex flex-col gap-4">
            {/* Title */}
            <h1 className="text-4xl font-bold text-gray-900 leading-tight tracking-tight">
              {currentPodcast.title || 'Untitled Podcast'}
            </h1>

            {/* Actions Row */}
            <div className="flex items-center justify-between mt-2">
              <div className="flex items-center gap-3">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusConfig.color}`}>
                  <StatusIcon className={`w-3.5 h-3.5 mr-1.5 ${currentPodcast.status === 'generating' ? 'animate-spin' : ''}`} />
                  {currentPodcast.status.charAt(0).toUpperCase() + currentPodcast.status.slice(1)}
                </span>
                <span className="text-sm text-gray-500 flex items-center">
                  <Calendar className="w-3.5 h-3.5 mr-1.5" />
                  {formatDate(currentPodcast.created_at)}
                </span>
              </div>

              <div className="flex items-center gap-2">
                {currentPodcast.status === 'completed' && onPlay && (
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => onPlay(currentPodcast)}
                    className="h-9 bg-purple-600 hover:bg-purple-700 text-white border-transparent"
                  >
                    <Play className="h-4 w-4 mr-2" />
                    Play
                  </Button>
                )}

                {currentPodcast.status === 'completed' && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onDownload(currentPodcast)}
                    className="h-9"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download
                  </Button>
                )}

                {onEdit && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onEdit(currentPodcast)}
                    className="h-9"
                  >
                    <Edit className="h-4 w-4 mr-2" />
                    Edit
                  </Button>
                )}

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onDelete(currentPodcast)}
                  className="h-9 text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200 hover:border-red-300"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Compact Metadata Grid */}
        <div className="mb-10 bg-gray-50/50 rounded-xl border border-gray-100 p-5">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-y-6 gap-x-8">
            <div className="space-y-1">
              <div className="flex items-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                <Tag className="w-3.5 h-3.5 mr-1.5" />
                Topic
              </div>
              <p className="text-sm font-medium text-gray-900 truncate" title={currentPodcast.topic}>
                {currentPodcast.topic || "—"}
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                <Clock className="w-3.5 h-3.5 mr-1.5" />
                Duration
              </div>
              <p className="text-sm font-medium text-gray-900 truncate">
                {currentPodcast.duration ? formatDuration(currentPodcast.duration) : '—'}
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                <Globe className="w-3.5 h-3.5 mr-1.5" />
                Language
              </div>
              <p className="text-sm font-medium text-gray-900 truncate">
                {currentPodcast.language === 'en' ? 'English' : currentPodcast.language === 'zh' ? 'Chinese' : currentPodcast.language || '—'}
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                <Mic className="w-3.5 h-3.5 mr-1.5" />
                Description
              </div>
              <p className="text-sm font-medium text-gray-900 truncate" title={currentPodcast.description}>
                {currentPodcast.description || "—"}
              </p>
            </div>
          </div>

          {currentPodcast.error_message && (
            <div className="mt-4 pt-4 border-t border-gray-200/60">
              <div className="flex items-start gap-2 text-red-600 bg-red-50/50 p-3 rounded-lg">
                <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                <div className="text-sm">
                  <span className="font-medium block mb-0.5">Error</span>
                  {currentPodcast.error_message}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Audio Player Section */}
        {currentPodcast.status === 'completed' && audioUrl && (
          <div className="mb-10">
            <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center">
              <Play className="w-4 h-4 mr-2 text-gray-400" />
              Audio Player
            </h3>
            <div className="bg-gray-50 rounded-xl p-6 border border-gray-100">
              <audio
                controls
                className="w-full"
                src={audioUrl}
              >
                Your browser does not support the audio element.
              </audio>
            </div>
          </div>
        )}

        {/* Transcript Section */}
        {currentPodcast.conversation_text && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-900 flex items-center">
              <FileText className="w-4 h-4 mr-2 text-gray-400" />
              Conversation Transcript
            </h3>
            <div className="prose max-w-none">
              <pre className="whitespace-pre-wrap text-sm text-gray-700 bg-gray-50 p-6 rounded-xl border border-gray-100 font-sans leading-relaxed">
                {currentPodcast.conversation_text}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PodcastDetail; 
