import React from "react";
import { useNavigate } from "react-router-dom";
import { Report, ReportCardProps } from "../types/type";

export default function ReportCard({
  report,
  onSelect,
  onDownload,
  onDelete,
  onEdit,
  isSelected
}: ReportCardProps) {
  const navigate = useNavigate();

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    // Use navigation to detail page instead of callback
    navigate(`/report/${report.id}`);

    // Keep backward compatibility - call onSelect if provided
    if (onSelect) {
      onSelect(report);
    }
  };

  const handleDownload = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDownload(report);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(report);
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onEdit) onEdit(report);
  };

  return (
    <div
      className={`border rounded-lg overflow-hidden shadow hover:shadow-lg transition-shadow cursor-pointer ${isSelected ? 'ring-2 ring-blue-500' : ''
        }`}
      onClick={handleClick}
    >
      {/* Cover Image or Placeholder */}
      <div className="h-40 bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <svg className="h-16 w-16 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>

      <div className="p-4">
        {/* Title */}
        <h3 className="font-semibold mb-2 text-gray-900 line-clamp-2">
          {report.title || report.article_title || 'Untitled Report'}
        </h3>
        {/* Date */}
        <span className="text-xs text-gray-500">
          {new Date(report.created_at).toLocaleDateString()}
        </span>
      </div>
    </div>
  );
}
