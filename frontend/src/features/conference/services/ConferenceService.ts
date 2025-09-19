// Conference Service - Handles all conference-related API operations
import { apiClient } from '@/shared/api';
import {
  Venue,
  Instance,
  Publication,
  DashboardResponse,
  ConferenceOverview,
  PaginatedResponse,
  DashboardParams,
  InstanceParams,
} from '../types';

export interface IConferenceService {
  getVenues(): Promise<Venue[]>;
  getInstances(params?: InstanceParams): Promise<Instance[]>;
  getPublications(params?: { instance?: number; page?: number; page_size?: number }): Promise<PaginatedResponse<Publication>>;
  getDashboard(params: DashboardParams): Promise<DashboardResponse>;
  getOverview(): Promise<ConferenceOverview>;
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
   * Get list of publications with optional filters
   */
  async getPublications(params?: {
    instance?: number;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Publication>> {
    return apiClient.get(`${this.baseEndpoint}/publications/`, { params });
  }

  /**
   * Get dashboard data with venue/year or instance filter
   */
  async getDashboard(params: DashboardParams): Promise<DashboardResponse> {
    return apiClient.get(`${this.baseEndpoint}/dashboard/`, { params });
  }

  /**
   * Get conferences overview statistics
   */
  async getOverview(): Promise<ConferenceOverview> {
    return apiClient.get(`${this.baseEndpoint}/dashboard/overview/`);
  }
}

// Export singleton instance
export const conferenceService = new ConferenceService();
