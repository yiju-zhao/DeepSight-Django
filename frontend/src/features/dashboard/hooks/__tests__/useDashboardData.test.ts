/**
 * Tests for useDashboardData hook
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useDashboardData } from '../useDashboardData';
import { server, mockApiError } from '@/test-utils/test-server';
import { config } from '@/config';

// Mock fetchJson utility
vi.mock('@/shared/utils/utils', () => ({
  fetchJson: vi.fn(),
}));

import { fetchJson } from '@/shared/utils/utils';
const mockFetchJson = vi.mocked(fetchJson);

describe('useDashboardData', () => {
  beforeEach(() => {
    server.resetHandlers();
    mockFetchJson.mockClear();
  });

  it('should initialize with loading state', () => {
    const { result } = renderHook(() => useDashboardData());

    expect(result.current.loading).toBe(true);
    expect(result.current.reports).toEqual([]);
    expect(result.current.podcasts).toEqual([]);
    expect(result.current.confsOverview).toBe(null);
    expect(result.current.orgsOverview).toBe(null);
    expect(result.current.error).toBe(null);
  });

  it('should fetch all dashboard data successfully', async () => {
    const mockReports = [
      { id: '1', title: 'Report 1', status: 'completed' },
      { id: '2', title: 'Report 2', status: 'running' },
    ];

    const mockPodcasts = [
      { id: '1', title: 'Podcast 1', status: 'completed' },
    ];

    const mockConferences = {
      total_conferences: 5,
      total_papers: 100,
      years_covered: 3,
      avg_papers_per_year: 33.3,
      conferences: [
        { name: 'NIPS', location: 'Montreal', year: '2024', summary: 'AI Conference' },
      ],
    };

    const mockOrganizations = {
      organizations: [
        { name: 'OpenAI', type: 'company', description: 'AI research company' },
      ],
    };

    // Mock successful responses
    mockFetchJson
      .mockResolvedValueOnce(mockReports)
      .mockResolvedValueOnce(mockPodcasts)
      .mockResolvedValueOnce(mockConferences)
      .mockResolvedValueOnce(mockOrganizations);

    const { result } = renderHook(() => useDashboardData());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.reports).toEqual(mockReports);
    expect(result.current.podcasts).toEqual(mockPodcasts);
    expect(result.current.confsOverview).toEqual(mockConferences);
    expect(result.current.orgsOverview).toEqual(mockOrganizations);
    expect(result.current.error).toBe(null);

    // Verify API calls were made
    expect(mockFetchJson).toHaveBeenCalledTimes(3);
    expect(mockFetchJson).toHaveBeenCalledWith(`${config.API_BASE_URL}/reports/`);
    expect(mockFetchJson).toHaveBeenCalledWith(`${config.API_BASE_URL}/podcasts/jobs/`);
    expect(mockFetchJson).toHaveBeenCalledWith(`${config.API_BASE_URL}/conferences/overview/general/`);
  });

  it('should handle partial failures gracefully', async () => {
    const mockReports = [{ id: '1', title: 'Report 1', status: 'completed' }];

    // Mock mixed success/failure responses
    mockFetchJson
      .mockResolvedValueOnce(mockReports) // reports - success
      .mockRejectedValueOnce(new Error('Podcasts failed')) // podcasts - failure
      .mockResolvedValueOnce(null) // conferences - success (null)
      .mockRejectedValueOnce(new Error('Organizations failed')); // organizations - failure

    const { result } = renderHook(() => useDashboardData());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.reports).toEqual(mockReports);
    expect(result.current.podcasts).toEqual([]); // Should default to empty array on failure
    expect(result.current.confsOverview).toBe(null); // Success but null response
    expect(result.current.orgsOverview).toBe(null); // Should default to null on failure
    expect(result.current.error).toBe(null); // No general error since it's partial failure
  });

  it('should handle complete failure', async () => {
    const error = new Error('Network error');
    mockFetchJson.mockRejectedValue(error);

    const { result } = renderHook(() => useDashboardData());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe('Network error');
    expect(result.current.reports).toEqual([]);
    expect(result.current.podcasts).toEqual([]);
    expect(result.current.confsOverview).toBe(null);
    expect(result.current.orgsOverview).toBe(null);
  });

  it('should update report in state', async () => {
    const mockReports = [
      { id: '1', title: 'Report 1', status: 'completed' },
      { id: '2', title: 'Report 2', status: 'running' },
    ];

    mockFetchJson.mockResolvedValue(mockReports);

    const { result } = renderHook(() => useDashboardData());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    act(() => {
      result.current.updateReport('1', { title: 'Updated Report 1', status: 'failed' });
    });

    expect(result.current.reports).toEqual([
      { id: '1', title: 'Updated Report 1', status: 'failed' },
      { id: '2', title: 'Report 2', status: 'running' },
    ]);
  });

  it('should delete report from state', async () => {
    const mockReports = [
      { id: '1', title: 'Report 1', status: 'completed' },
      { id: '2', title: 'Report 2', status: 'running' },
    ];

    mockFetchJson.mockResolvedValue(mockReports);

    const { result } = renderHook(() => useDashboardData());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    act(() => {
      result.current.deleteReport('1');
    });

    expect(result.current.reports).toEqual([
      { id: '2', title: 'Report 2', status: 'running' },
    ]);
  });

  it('should update podcast in state', async () => {
    const mockPodcasts = [
      { id: '1', title: 'Podcast 1', status: 'completed' },
    ];

    mockFetchJson.mockResolvedValue(mockPodcasts);

    const { result } = renderHook(() => useDashboardData());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    act(() => {
      result.current.updatePodcast('1', { title: 'Updated Podcast 1', status: 'failed' });
    });

    expect(result.current.podcasts).toEqual([
      { id: '1', title: 'Updated Podcast 1', status: 'failed' },
    ]);
  });

  it('should refresh data when refreshData is called', async () => {
    const mockReports = [{ id: '1', title: 'Report 1', status: 'completed' }];
    mockFetchJson.mockResolvedValue(mockReports);

    const { result } = renderHook(() => useDashboardData());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(mockFetchJson).toHaveBeenCalledTimes(4);

    act(() => {
      result.current.refreshData();
    });

    // Should trigger another loading cycle
    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Should have called fetchJson again
    expect(mockFetchJson).toHaveBeenCalledTimes(8); // 4 initial + 4 refresh
  });
});