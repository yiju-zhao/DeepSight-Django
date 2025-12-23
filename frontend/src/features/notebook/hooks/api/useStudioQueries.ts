/**
 * Studio Queries - TanStack Query hooks for reports and podcasts
 * 
 * Includes data normalization via `select` to provide clean data to components.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { reportsApi, podcastsApi, studioApi } from '@/features/notebook/api/studioApi';
import type { ReportJobRaw, PodcastJobRaw } from '@/features/notebook/api/studioApi';
import { studioKeys } from './queryKeys';
import type { StudioItemStatus } from '@/features/notebook/types/studioItem';

// ============================================================================
// Type Definitions
// ============================================================================

export interface NormalizedReportJob {
    id: string;
    status: StudioItemStatus;
    title: string;
    createdAt: string;
    completedAt?: string;
    markdown?: string;
    content?: string;
    pdfAvailable?: boolean;
    articleTitle?: string;
}

export interface NormalizedPodcastJob {
    id: string;
    status: StudioItemStatus;
    title: string;
    createdAt: string;
    completedAt?: string;
    description?: string;
    audioUrl?: string;
    duration?: number;
}

// ============================================================================
// Normalization Helpers
// ============================================================================

function normalizeStatus(status: string): StudioItemStatus {
    const statusMap: Record<string, StudioItemStatus> = {
        'pending': 'generating',
        'processing': 'generating',
        'running': 'generating',
        'completed': 'completed',
        'done': 'completed',
        'failed': 'failed',
        'error': 'failed',
        'cancelled': 'cancelled',
    };
    return statusMap[status.toLowerCase()] || 'idle';
}

function normalizeReportJob(job: ReportJobRaw): NormalizedReportJob {
    return {
        id: job.id || job.report_id || '',
        status: normalizeStatus(job.status),
        title: job.title || job.article_title || 'Untitled Report',
        createdAt: job.created_at,
        completedAt: job.completed_at,
        markdown: job.markdown,
        content: job.content,
        pdfAvailable: job.pdf_available,
        articleTitle: job.article_title,
    };
}

function normalizePodcastJob(job: PodcastJobRaw): NormalizedPodcastJob {
    return {
        id: job.id || job.job_id || '',
        status: normalizeStatus(job.status),
        title: job.title || 'Untitled Podcast',
        createdAt: job.created_at,
        completedAt: job.completed_at,
        description: job.description,
        audioUrl: job.audio_url,
        duration: job.duration,
    };
}

// ============================================================================
// Models Query
// ============================================================================

export const useAvailableModels = () => {
    return useQuery({
        queryKey: studioKeys.models(),
        queryFn: () => studioApi.getAvailableModels(),
        staleTime: 30 * 60 * 1000, // 30 minutes
        gcTime: 60 * 60 * 1000, // 1 hour
    });
};

// ============================================================================
// Report Queries
// ============================================================================

export const useReportJobs = (notebookId: string) => {
    return useQuery({
        queryKey: studioKeys.reports(notebookId),
        queryFn: () => reportsApi.list(notebookId),
        enabled: !!notebookId,
        staleTime: 30 * 1000, // 30 seconds
        select: (data) => data.map(normalizeReportJob),
    });
};

export const useReportContent = (notebookId: string, jobId: string, enabled = true) => {
    return useQuery({
        queryKey: studioKeys.reportContent(notebookId, jobId),
        queryFn: () => reportsApi.getContent(jobId),
        enabled: enabled && !!notebookId && !!jobId,
        staleTime: 5 * 60 * 1000,
    });
};

export const useReportStatus = (notebookId: string, jobId: string, enabled = true) => {
    return useQuery({
        queryKey: studioKeys.reportDetail(notebookId, jobId),
        queryFn: () => reportsApi.getStatus(jobId),
        enabled: enabled && !!notebookId && !!jobId,
        staleTime: 10 * 1000, // 10 seconds for status polling
        refetchInterval: (query) => {
            const data = query.state.data;
            // Stop polling when completed or failed
            if (data?.status === 'completed' || data?.status === 'failed') {
                return false;
            }
            return 5000; // Poll every 5 seconds
        },
        select: (data) => normalizeReportJob(data),
    });
};

// ============================================================================
// Report Mutations
// ============================================================================

export const useGenerateReport = (notebookId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (config: any) => reportsApi.generate(config, notebookId),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: studioKeys.reports(notebookId),
            });
        },
    });
};

export const useDeleteReport = (notebookId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (jobId: string) => reportsApi.delete(jobId),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: studioKeys.reports(notebookId),
            });
        },
    });
};

export const useCancelReport = (notebookId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (jobId: string) => reportsApi.cancel(jobId),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: studioKeys.reports(notebookId),
            });
        },
    });
};

export const useUpdateReport = (notebookId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ jobId, content }: { jobId: string; content: string }) =>
            reportsApi.update(jobId, content),
        onSuccess: (_, { jobId }) => {
            queryClient.invalidateQueries({
                queryKey: studioKeys.reportDetail(notebookId, jobId),
            });
        },
    });
};

// ============================================================================
// Podcast Queries
// ============================================================================

export const usePodcastJobs = (notebookId: string) => {
    return useQuery({
        queryKey: studioKeys.podcasts(notebookId),
        queryFn: () => podcastsApi.list(notebookId),
        enabled: !!notebookId,
        staleTime: 30 * 1000, // 30 seconds
        select: (data) =>
            data
                .map(normalizePodcastJob)
                .filter(job => job.status !== 'cancelled'), // Hide cancelled podcasts
    });
};

export const usePodcastStatus = (notebookId: string, jobId: string, enabled = true) => {
    return useQuery({
        queryKey: studioKeys.podcastDetail(notebookId, jobId),
        queryFn: () => podcastsApi.getStatus(jobId),
        enabled: enabled && !!notebookId && !!jobId,
        staleTime: 10 * 1000,
        refetchInterval: (query) => {
            const data = query.state.data;
            if (data?.status === 'completed' || data?.status === 'failed') {
                return false;
            }
            return 5000;
        },
        select: (data) => normalizePodcastJob(data),
    });
};

// ============================================================================
// Podcast Mutations
// ============================================================================

export const useGeneratePodcast = (notebookId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (formData: FormData) => podcastsApi.generate(formData, notebookId),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: studioKeys.podcasts(notebookId),
            });
        },
    });
};

export const useDeletePodcast = (notebookId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (jobId: string) => podcastsApi.delete(jobId),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: studioKeys.podcasts(notebookId),
            });
        },
    });
};

export const useCancelPodcast = (notebookId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (jobId: string) => podcastsApi.cancel(jobId),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: studioKeys.podcasts(notebookId),
            });
        },
    });
};
