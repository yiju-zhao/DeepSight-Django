import React, { useState, useEffect } from 'react';
import { Loader2, CheckCircle, AlertCircle, XCircle, ExternalLink, Info } from 'lucide-react';
import { conferenceService } from '../services/ConferenceService';
import { Popover, PopoverContent, PopoverTrigger } from '@/shared/components/ui/popover';
import type { ActiveImport } from '../types';

interface ImportStatusIndicatorProps {
    onRefresh?: () => void;
}

export const ImportStatusIndicator: React.FC<ImportStatusIndicatorProps> = ({ onRefresh }) => {
    const [imports, setImports] = useState<ActiveImport[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string>('');
    const [isOpen, setIsOpen] = useState(false);

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
        return undefined;
    }, [imports.length > 0]); // Re-run effect when imports change to check if we need to keep polling

    const fetchImportStatus = async () => {
        try {
            // Don't set loading state for background polling to avoid UI flicker
            if (imports.length === 0) setLoading(true);

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
            case 'processing':
                return <Loader2 className="animate-spin text-blue-500" size={16} />;
            case 'completed':
                return <CheckCircle className="text-green-500" size={16} />;
            case 'failed':
                return <XCircle className="text-red-500" size={16} />;
            case 'partially_completed':
                return <AlertCircle className="text-yellow-500" size={16} />;
            default:
                return null;
        }
    };

    const getStatusLabel = (status: ActiveImport['status']) => {
        switch (status) {
            case 'pending': return 'Pending';
            case 'processing': return 'Processing';
            case 'completed': return 'Completed';
            case 'failed': return 'Failed';
            case 'partially_completed': return 'Partially Completed';
            default: return status;
        }
    };

    const getStatusColor = (status: ActiveImport['status']) => {
        switch (status) {
            case 'pending':
            case 'processing': return 'text-blue-600';
            case 'completed': return 'text-green-600';
            case 'failed': return 'text-red-600';
            case 'partially_completed': return 'text-yellow-600';
            default: return 'text-gray-600';
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

    const activeImportsCount = imports.filter(
        i => i.status === 'pending' || i.status === 'processing'
    ).length;

    return (
        <Popover open={isOpen} onOpenChange={setIsOpen}>
            <PopoverTrigger asChild>
                <button
                    className={`flex items-center justify-center w-10 h-10 rounded-full transition-all duration-300 ${activeImportsCount > 0
                        ? 'bg-blue-50 text-blue-600 hover:bg-blue-100 ring-2 ring-blue-100'
                        : 'bg-white text-gray-500 hover:bg-gray-50 border border-[#E3E3E3]'
                        }`}
                    title="Import Status"
                >
                    {activeImportsCount > 0 ? (
                        <Loader2 className="animate-spin h-5 w-5" />
                    ) : (
                        <Info className="h-5 w-5" />
                    )}
                </button>
            </PopoverTrigger>
            <PopoverContent className="w-96 p-0" align="end">
                <div className="px-4 py-3 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                    <h3 className="font-semibold text-sm text-gray-900">Import Status</h3>
                    {activeImportsCount > 0 && (
                        <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
                            {activeImportsCount} active
                        </span>
                    )}
                </div>

                <div className="max-h-[400px] overflow-y-auto">
                    {loading && imports.length === 0 ? (
                        <div className="flex justify-center py-8">
                            <Loader2 className="animate-spin text-gray-400" size={24} />
                        </div>
                    ) : error ? (
                        <div className="p-4 text-sm text-red-600 bg-red-50 text-center">
                            {error}
                        </div>
                    ) : imports.length === 0 ? (
                        <div className="py-12 text-center">
                            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-3">
                                <Info className="w-6 h-6 text-gray-400" />
                            </div>
                            <p className="text-sm text-gray-500">No recent imports</p>
                        </div>
                    ) : (
                        <div className="divide-y divide-gray-100">
                            {imports.map((importJob) => (
                                <div key={importJob.batch_job_id} className="p-4 hover:bg-gray-50 transition-colors">
                                    <div className="flex items-start space-x-3">
                                        <div className="mt-0.5 flex-shrink-0">
                                            {getStatusIcon(importJob.status)}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center justify-between mb-1">
                                                <a
                                                    href={`/deepdive/${importJob.notebook_id}`}
                                                    className="text-sm font-medium text-gray-900 hover:text-blue-600 truncate block max-w-[180px]"
                                                    title={importJob.notebook_name}
                                                >
                                                    {importJob.notebook_name}
                                                </a>
                                                <span className="text-xs text-gray-400 flex-shrink-0 ml-2">
                                                    {formatDate(importJob.updated_at)}
                                                </span>
                                            </div>

                                            <div className="flex items-center justify-between text-xs mt-1">
                                                <span className={getStatusColor(importJob.status)}>
                                                    {getStatusLabel(importJob.status)}
                                                </span>
                                                <span className="text-gray-500">
                                                    {importJob.completed_items}/{importJob.total_items}
                                                </span>
                                            </div>

                                            {(importJob.status === 'pending' || importJob.status === 'processing') && (
                                                <div className="mt-2 w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                                                    <div
                                                        className="bg-blue-500 h-full rounded-full transition-all duration-500 ease-out"
                                                        style={{ width: `${importJob.progress_percentage}%` }}
                                                    />
                                                </div>
                                            )}

                                            {importJob.failed_items > 0 && (
                                                <div className="mt-1.5 text-xs text-red-600 flex items-center">
                                                    <AlertCircle size={12} className="mr-1" />
                                                    {importJob.failed_items} failed
                                                </div>
                                            )}
                                        </div>
                                        <a
                                            href={`/deepdive/${importJob.notebook_id}`}
                                            className="text-gray-400 hover:text-blue-600 transition-colors mt-0.5"
                                            title="Go to Notebook"
                                        >
                                            <ExternalLink size={14} />
                                        </a>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </PopoverContent>
        </Popover>
    );
};
