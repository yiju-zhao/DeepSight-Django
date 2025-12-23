/**
 * Source API - Source management operations
 * 
 * Pure API calls for source/file operations within notebooks.
 */

import { apiClient } from '@/shared/api/client';
import { PaginatedResponse, PaginationParams } from '@/shared/api/types';
import type {
    Source,
    CreateSourceRequest,
    UpdateSourceRequest,
    ProcessUrlRequest,
    AddTextRequest,
} from '@/shared/types/notebook';

export const sourceApi = {
    // ============================================================================
    // Core CRUD Operations
    // ============================================================================

    getAll: (notebookId: string, params?: PaginationParams): Promise<PaginatedResponse<Source>> =>
        apiClient.get(`/notebooks/${notebookId}/sources/`, params ? { params } : {}),

    getById: (notebookId: string, sourceId: string): Promise<Source> =>
        apiClient.get(`/notebooks/${notebookId}/sources/${sourceId}/`),

    create: (notebookId: string, data: CreateSourceRequest): Promise<Source> =>
        apiClient.post(`/notebooks/${notebookId}/sources/`, data),

    update: (notebookId: string, sourceId: string, data: UpdateSourceRequest): Promise<Source> =>
        apiClient.patch(`/notebooks/${notebookId}/sources/${sourceId}/`, data),

    delete: (notebookId: string, sourceId: string): Promise<void> =>
        apiClient.delete(`/notebooks/${notebookId}/sources/${sourceId}/`),

    // ============================================================================
    // File Upload
    // ============================================================================

    uploadFile: (notebookId: string, file: File): Promise<Source> => {
        const formData = new FormData();
        formData.append('file', file);
        return apiClient.post(`/notebooks/${notebookId}/sources/`, formData);
    },

    // ============================================================================
    // URL Processing
    // ============================================================================

    processUrl: (notebookId: string, data: ProcessUrlRequest): Promise<Source> =>
        apiClient.post(`/notebooks/${notebookId}/sources/process-url/`, data),

    // ============================================================================
    // Text Content
    // ============================================================================

    addText: (notebookId: string, data: AddTextRequest): Promise<Source> =>
        apiClient.post(`/notebooks/${notebookId}/sources/add-text/`, data),
};
