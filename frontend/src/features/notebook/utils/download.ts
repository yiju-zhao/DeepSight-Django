/**
 * Download Utilities
 * 
 * Extracted from StudioService.ts - handles file downloads with
 * redirect handling for MinIO presigned URLs.
 */

import { apiClient } from '@/shared/api/client';

// ============================================================================
// Cookie Helper
// ============================================================================

function getCookie(name: string): string | null {
    const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
    return match?.[2] ? decodeURIComponent(match[2]) : null;
}

// ============================================================================
// Download with Redirect Handling
// ============================================================================

/**
 * Downloads a file from the API with redirect handling for MinIO presigned URLs.
 * 
 * Handles 301/302 redirects by:
 * 1. Making initial authenticated request to Django
 * 2. Following redirect to MinIO without credentials (avoiding CORS issues)
 * 3. Returning the blob for the file
 */
export async function downloadWithRedirect(
    url: string,
    options: {
        filename?: string;
        credentials?: RequestCredentials;
    } = {}
): Promise<Blob> {
    const fullUrl = url.startsWith('http') ? url : `${apiClient.getBaseUrl()}${url}`;
    const queryParams = options.filename
        ? `?filename=${encodeURIComponent(options.filename)}`
        : '';

    let response: Response;

    try {
        response = await fetch(`${fullUrl}${queryParams}`, {
            method: 'GET',
            credentials: options.credentials ?? 'include',
            headers: {
                'X-CSRFToken': getCookie('csrftoken') ?? '',
            },
            redirect: 'manual'
        });
    } catch (fetchError: unknown) {
        const error = fetchError as Error;
        console.error('Network request failed:', error.message);

        if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
            throw new Error('Network connectivity or CORS issue. Check console for details.');
        } else if (error.message.includes('NetworkError') || error.message.includes('net::ERR_FAILED')) {
            throw new Error('Network error - server may be down or unreachable.');
        }

        throw new Error(`Network request failed: ${error.message}`);
    }

    // Handle redirect to MinIO
    if (response.status === 302 || response.status === 301) {
        const redirectUrl = response.headers.get('Location');
        if (!redirectUrl) {
            throw new Error('No redirect URL found in response headers');
        }

        const minioResponse = await fetch(redirectUrl, {
            method: 'GET',
            credentials: 'omit', // Don't send cookies to MinIO
            mode: 'cors'
        });

        if (!minioResponse.ok) {
            throw new Error(`MinIO download failed: ${minioResponse.status} ${minioResponse.statusText}`);
        }

        return minioResponse.blob();
    }

    // Direct response (no redirect)
    if (response.ok) {
        return response.blob();
    }

    // Error handling
    let errorMessage = `HTTP ${response.status}`;
    try {
        const errorData = await response.json();
        errorMessage = errorData.error || errorData.detail || errorMessage;
    } catch {
        errorMessage = response.statusText || errorMessage;
    }
    throw new Error(errorMessage);
}

// ============================================================================
// Browser Download Trigger
// ============================================================================

/**
 * Triggers a browser download for a blob.
 */
export function triggerBlobDownload(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    window.URL.revokeObjectURL(url);
    link.remove();
}

/**
 * Triggers a browser download via URL (uses browser's native download mechanism).
 * Useful for authenticated endpoints that redirect to external storage.
 */
export function triggerUrlDownload(url: string): void {
    const fullUrl = url.startsWith('http') ? url : `${apiClient.getBaseUrl()}${url}`;
    const link = document.createElement('a');
    link.href = fullUrl;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    link.remove();
}

// ============================================================================
// Specific Download Functions (convenience wrappers)
// ============================================================================

/**
 * Downloads a report file (markdown, PDF, etc.)
 */
export async function downloadReportFile(
    jobId: string,
    filename?: string
): Promise<Blob> {
    const url = `/reports/${jobId}/download/`;
    return downloadWithRedirect(url, { filename });
}

/**
 * Downloads a report as PDF
 */
export async function downloadReportPdf(jobId: string): Promise<Blob> {
    return downloadWithRedirect(`/reports/${jobId}/download-pdf/`);
}

/**
 * Triggers podcast audio download (uses browser's native download)
 */
export function downloadPodcastAudio(jobId: string): void {
    triggerUrlDownload(`/podcasts/${jobId}/audio/?download=1`);
}
