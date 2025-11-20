import React from "react";
import { Podcast, PodcastCardProps } from "../types/type";

export default function PodcastCard({
  podcast,
  onSelect,
  onDownload,
  onDelete,
  onPlay,
  onEdit,
  isSelected
}: PodcastCardProps) {
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelect(podcast);
  };

  const handleDownload = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDownload(podcast);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(podcast);
  };

  const handlePlay = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onPlay) onPlay(podcast);
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onEdit) onEdit(podcast);
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '';
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div
      className={`border rounded-lg overflow-hidden shadow hover:shadow-lg transition-shadow cursor-pointer ${isSelected ? 'ring-2 ring-purple-500' : ''
        }`}
      onClick={handleClick}
    >
      {/* Cover Image or Placeholder */}
      <div className="h-40 bg-gradient-to-br from-purple-50 to-indigo-100 flex items-center justify-center">
        <svg className="h-16 w-16 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
        </svg>
      </div>

      <div className="p-4">
        {/* Title */}
        <h3 className="font-semibold mb-2 text-gray-900 line-clamp-2">
          {podcast.title || 'Untitled Podcast'}
        </h3>
        {/* Date */}
        <span className="text-xs text-gray-500">
          {new Date(podcast.created_at).toLocaleDateString()}
        </span>
      </div>
    </div>
  );
} 