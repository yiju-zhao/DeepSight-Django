/**
 * Custom hook for managing dashboard data
 * Consolidates all data fetching logic for the dashboard
 */

import { useState, useEffect } from 'react';
import { fetchJson } from '@/shared/utils/utils';
import { config } from '@/config';

export interface Report {
  id: string;
  title: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  updated_at: string;
  content?: string;
  description?: string;
  [key: string]: any;
}

export interface Podcast {
  id: string;
  title: string;
  status: 'pending' | 'generating' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  updated_at: string;
  description?: string;
  topic?: string;
  audioUrl?: string;
  audio_file?: string;
  duration?: number;
  [key: string]: any;
}

export interface Conference {
  name: string;
  location: string;
  year: string;
  summary: string;
}

export interface Organization {
  name: string;
  type: string;
  description: string;
  [key: string]: any;
}

export interface ConferencesOverview {
  total_conferences: number;
  total_papers: number;
  years_covered: number;
  avg_papers_per_year: number;
  conferences: Conference[];
}

export interface OrganizationsOverview {
  organizations: Organization[];
}

export interface DashboardData {
  reports: Report[];
  podcasts: Podcast[];
  confsOverview: ConferencesOverview | null;
  orgsOverview: OrganizationsOverview | null;
}

export function useDashboardData() {
  const [data, setData] = useState<DashboardData>({
    reports: [],
    podcasts: [],
    confsOverview: null,
    orgsOverview: null,
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);

    try {
      const [reports, podcasts, confsOverview, orgsOverview] = await Promise.allSettled([
        fetchJson(`${config.API_BASE_URL}/reports/trending`),
        fetchJson(`${config.API_BASE_URL}/podcasts/`),
        fetchJson(`${config.API_BASE_URL}/conferences/overview`),
        fetchJson(`${config.API_BASE_URL}/organizations/overview`),
      ]);

      setData({
        reports: reports.status === 'fulfilled' ? reports.value : [],
        podcasts: podcasts.status === 'fulfilled' ? podcasts.value : [],
        confsOverview: confsOverview.status === 'fulfilled' ? confsOverview.value : null,
        orgsOverview: orgsOverview.status === 'fulfilled' ? orgsOverview.value : null,
      });

      // Log any failed requests
      [reports, podcasts, confsOverview, orgsOverview].forEach((result, index) => {
        if (result.status === 'rejected') {
          const endpoints = ['reports', 'podcasts', 'conferences', 'organizations'];
          console.warn(`Failed to load ${endpoints[index]}:`, result.reason);
        }
      });
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to load dashboard data');
      console.error('Dashboard data loading error:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const refreshData = () => {
    loadDashboardData();
  };

  const updateReport = (reportId: string, updates: Partial<Report>) => {
    setData(prev => ({
      ...prev,
      reports: prev.reports.map(report =>
        report.id === reportId ? { ...report, ...updates } : report
      ),
    }));
  };

  const deleteReport = (reportId: string) => {
    setData(prev => ({
      ...prev,
      reports: prev.reports.filter(report => report.id !== reportId),
    }));
  };

  const updatePodcast = (podcastId: string, updates: Partial<Podcast>) => {
    setData(prev => ({
      ...prev,
      podcasts: prev.podcasts.map(podcast =>
        podcast.id === podcastId ? { ...podcast, ...updates } : podcast
      ),
    }));
  };

  return {
    ...data,
    loading,
    error,
    refreshData,
    updateReport,
    deleteReport,
    updatePodcast,
  };
}