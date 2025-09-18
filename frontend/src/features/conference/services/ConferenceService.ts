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
  private readonly baseEndpoint = '/api/v1/conferences';

  /**
   * Get list of venues
   */
  async getVenues(): Promise<Venue[]> {
    return apiClient.get(`${this.baseEndpoint}/venues/`);
  }

  /**
   * Get list of instances with optional venue filter
   */
  async getInstances(params?: InstanceParams): Promise<Instance[]> {
    return apiClient.get(`${this.baseEndpoint}/instances/`, { params });
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
    return apiClient.get(`${this.baseEndpoint}/dashboard/dashboard/`, { params });
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