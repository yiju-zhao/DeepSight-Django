// Conference Service - Handles all conference-related API operations
import { apiClient } from '@/shared/api';
import {
  Venue,
  Instance,
  Publication,
  PublicationTableItem,
  DashboardResponse,
  ConferenceOverview,
  PaginatedResponse,
  DashboardParams,
  InstanceParams,
  ImportToNotebookRequest,
  ImportResponse,
  ActiveImport,
  Session,
} from '../types';

export interface IConferenceService {
  getVenues(): Promise<Venue[]>;
  getInstances(params?: InstanceParams): Promise<Instance[]>;
  getSessions(params?: { instance?: number }): Promise<Session[]>;
  getPublications(params?: { instance?: number; page?: number; page_size?: number; search?: string; ordering?: string }): Promise<PaginatedResponse<PublicationTableItem>>;
  getDashboard(params: DashboardParams): Promise<DashboardResponse>;
  getOverview(): Promise<ConferenceOverview>;
  importToNotebook(request: ImportToNotebookRequest): Promise<ImportResponse>;
  getImportStatus(): Promise<ActiveImport[]>;
}

export class ConferenceService implements IConferenceService {
  private readonly baseEndpoint = '/conferences';

  /**
   * Get list of venues
   */
  async getVenues(): Promise<Venue[]> {
    const res = await apiClient.get(`${this.baseEndpoint}/venues/`, { params: { page_size: 1000 } });
    // Handle paginated or non-paginated responses
    return Array.isArray(res) ? res as Venue[] : (res?.results ?? []);
  }

  /**
   * Get list of instances with optional venue filter
   */
  async getInstances(params?: InstanceParams): Promise<Instance[]> {
    const res = await apiClient.get(`${this.baseEndpoint}/instances/`, { params: { ...(params || {}), page_size: 1000 } });
    return Array.isArray(res) ? res as Instance[] : (res?.results ?? []);
  }

  /**
   * Get list of sessions with optional instance filter
   */
  async getSessions(params?: { instance?: number }): Promise<Session[]> {
    const res = await apiClient.get(`${this.baseEndpoint}/sessions/`, { params: { ...(params || {}), page_size: 1000 } });
    return Array.isArray(res) ? res as Session[] : (res?.results ?? []);
  }

  /**
   * Get list of publications with optional filters
   */
  async getPublications(params?: {
    instance?: number;
    page?: number;
    page_size?: number;
    search?: string;
    ordering?: string;
  }): Promise<PaginatedResponse<PublicationTableItem>> {
    return apiClient.get(`${this.baseEndpoint}/publications/`, { params });
  }

  /**
   * Get dashboard data with instance filter (KPIs and charts only)
   */
  async getDashboard(params: DashboardParams): Promise<DashboardResponse> {
    return apiClient.get(`${this.baseEndpoint}/overview/`, { params });
  }

  /**
   * Get conferences overview statistics (general overview, not instance-specific)
   */
  async getOverview(): Promise<ConferenceOverview> {
    // Note: This is currently unused in ConferenceDashboard but kept for compatibility
    return apiClient.get(`${this.baseEndpoint}/overview/general/`);
  }

  /**
   * Import publications to a notebook
   */
  async importToNotebook(request: ImportToNotebookRequest): Promise<ImportResponse> {
    return apiClient.post(`${this.baseEndpoint}/publications/import-to-notebook/`, request);
  }

  /**
   * Get active and recent import jobs status
   */
  async getImportStatus(): Promise<ActiveImport[]> {
    return apiClient.get(`${this.baseEndpoint}/publications/import-status/`);
  }
}

// Export singleton instance
export const conferenceService = new ConferenceService();
