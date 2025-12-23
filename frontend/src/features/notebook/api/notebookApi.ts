/**
 * Notebook API - Core CRUD operations
 * 
 * Pure API calls for notebook management.
 */

import { apiClient } from '@/shared/api/client';
import { PaginatedResponse } from '@/shared/api/types';
import type {
    Notebook,
    CreateNotebookRequest,
    UpdateNotebookRequest,
    NotebookStats,
    GetNotebooksParams,
} from '@/shared/types/notebook';

export const notebookApi = {
    // ============================================================================
    // Core CRUD Operations
    // ============================================================================

    getAll: (params?: GetNotebooksParams): Promise<PaginatedResponse<Notebook>> =>
        apiClient.get('/notebooks/', params ? { params } : {}),

    getById: (id: string): Promise<Notebook> =>
        apiClient.get(`/notebooks/${id}/`),

    create: (data: CreateNotebookRequest): Promise<Notebook> =>
        apiClient.post('/notebooks/', data),

    update: (id: string, data: UpdateNotebookRequest): Promise<Notebook> =>
        apiClient.patch(`/notebooks/${id}/`, data),

    delete: (id: string): Promise<void> =>
        apiClient.delete(`/notebooks/${id}/`),

    // ============================================================================
    // Custom Actions
    // ============================================================================

    getStats: (id: string): Promise<NotebookStats> =>
        apiClient.get(`/notebooks/${id}/stats/`),

    duplicate: (id: string, name?: string): Promise<Notebook> =>
        apiClient.post(`/notebooks/${id}/duplicate/`, { name }),

    cleanupEmpty: (id: string): Promise<{ removed: number }> =>
        apiClient.post(`/notebooks/${id}/cleanup-empty/`),
};
