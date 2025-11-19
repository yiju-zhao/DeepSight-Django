import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, Loader2, CheckCircle, AlertCircle, XCircle, ExternalLink } from 'lucide-react';
import { conferenceService } from '../services/ConferenceService';
import type { ActiveImport } from '../types';

interface ImportStatusPanelProps {
  onRefresh?: () => void;
}

export const ImportStatusPanel: React.FC<ImportStatusPanelProps> = ({ onRefresh }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [imports, setImports] = useState<ActiveImport[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  // Poll for updates every 3 seconds when there are active imports
  useEffect(() => {
    fetchImportStatus();

    const hasActiveImports = imports.some(
      (imp) => imp.status === 'pending' || imp.status === 'processing'
    );

    if (hasActiveImports) {
      const interval = setInterval(fetchImportStatus, 3000);
      return () => clearInterval(interval);
    }
  }, [imports.length > 0]);

  const fetchImportStatus = async () => {
    try {
      setLoading(true);
      const data = await conferenceService.getImportStatus();
      setImports(data);
      setError('');

      // Trigger refresh callback if provided and there are completed imports
      if (onRefresh) {
        const hasCompletedImports = data.some(
          (imp) => imp.status === 'completed' || imp.status === 'partially_completed'
        );
        if (hasCompletedImports) {
          onRefresh();
        }
      }
    } catch (err: any) {
      setError('Failed to load import status');
      console.error('Error fetching import status:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: ActiveImport['status']) => {
    switch (status) {
      case 'pending':
        return <Loader2 className="animate-spin text-blue-500" size={20} />;
      case 'processing':
        return <Loader2 className="animate-spin text-blue-500" size={20} />;
      case 'completed':
        return <CheckCircle className="text-green-500" size={20} />;
      case 'failed':
        return <XCircle className="text-red-500" size={20} />;
      case 'partially_completed':
        return <AlertCircle className="text-yellow-500" size={20} />;
      default:
        return null;
    }
  };

  const getStatusLabel = (status: ActiveImport['status']) => {
    switch (status) {
      case 'pending':
        return 'Pending';
      case 'processing':
        return 'Processing';
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      case 'partially_completed':
        return 'Partially Completed';
      default:
        return status;
    }
  };

  const getStatusColor = (status: ActiveImport['status']) => {
    switch (status) {
      case 'pending':
      case 'processing':
        return 'text-blue-600';
      case 'completed':
        return 'text-green-600';
      case 'failed':
        return 'text-red-600';
      case 'partially_completed':
        return 'text-yellow-600';
      default:
        return 'text-gray-600';
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    return date.toLocaleDateString();
  };

  // Don't show panel if there are no imports
  if (imports.length === 0 && !loading) {
    return null;
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-gray-200 shadow-lg">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-6 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center space-x-3">
          <span className="font-medium text-gray-900">
            Import Status
          </span>
          {imports.length > 0 && (
            <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
              {imports.length} {imports.length === 1 ? 'job' : 'jobs'}
            </span>
          )}
          {loading && (
            <Loader2 className="animate-spin text-gray-400" size={16} />
          )}
        </div>
        {isExpanded ? <ChevronDown size={20} /> : <ChevronUp size={20} />}
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="max-h-96 overflow-y-auto border-t border-gray-100">
          {error && (
            <div className="px-6 py-3 bg-red-50 text-red-700 text-sm">
              {error}
            </div>
          )}

          {imports.length === 0 && !loading ? (
            <div className="px-6 py-8 text-center text-gray-500">
              No recent imports
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {imports.map((importJob) => (
                <div key={importJob.batch_job_id} className="px-6 py-4 hover:bg-gray-50">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-3 flex-1">
                      {getStatusIcon(importJob.status)}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <a
                            href={`/notebooks/${importJob.notebook_id}`}
                            className="font-medium text-gray-900 hover:text-blue-600 truncate"
                            title={importJob.notebook_name}
                          >
                            {importJob.notebook_name}
                          </a>
                          <ExternalLink size={14} className="text-gray-400" />
                        </div>

                        <div className="flex items-center space-x-4 mt-1 text-sm text-gray-600">
                          <span className={getStatusColor(importJob.status)}>
                            {getStatusLabel(importJob.status)}
                          </span>
                          <span>
                            {importJob.completed_items} / {importJob.total_items} items
                          </span>
                          {importJob.failed_items > 0 && (
                            <span className="text-red-600">
                              {importJob.failed_items} failed
                            </span>
                          )}
                          <span className="text-gray-400">
                            {formatDate(importJob.updated_at)}
                          </span>
                        </div>

                        {/* Progress Bar */}
                        {(importJob.status === 'pending' || importJob.status === 'processing') && (
                          <div className="mt-2">
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div
                                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                style={{ width: `${importJob.progress_percentage}%` }}
                              />
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {importJob.progress_percentage.toFixed(1)}% complete
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
