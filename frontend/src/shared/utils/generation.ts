// ====== SHARED GENERATION UTILITIES ======
// Common utilities for report and podcast generation

import React, { useState, useCallback, useEffect } from 'react';
import { config } from "@/config";

// ====== GENERATION STATE MANAGEMENT ======

export enum GenerationState {
  IDLE = 'idle',
  GENERATING = 'generating', 
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export interface GenerationConfig {
  model: string;
  temperature?: number;
  maxTokens?: number;
  systemPrompt?: string;
  [key: string]: any;
}

export interface ReportConfig extends GenerationConfig {
  topic?: string;
  article_title?: string;
  model_provider?: string;
  retriever?: string;
  prompt_type?: string;
  include_image?: boolean;
  include_domains?: boolean;
  time_range?: string;
  notebook_id?: string;
  source_ids?: string[];
}

export interface PodcastConfig extends GenerationConfig {
  title?: string;
  description?: string;
  topic?: string;
  expert_names?: {
    host?: string;
    expert1?: string;
    expert2?: string;
  };
  notebook_id?: string;
  source_file_ids?: string[];
}

// ====== JOB MANAGEMENT ======

export interface JobData {
  id: string;
  type: 'report' | 'podcast';
  status: GenerationState;
  progress?: string;
  config: any;
  created_at: string;
  notebook_id?: string;
}

export class JobService {
  private static instance: JobService;
  private subscribers: Map<string, (data: any) => void> = new Map();

  static getInstance(): JobService {
    if (!JobService.instance) {
      JobService.instance = new JobService();
    }
    return JobService.instance;
  }

  subscribe(jobId: string, onUpdate: (data: any) => void): void {
    this.subscribers.set(jobId, onUpdate);
  }

  unsubscribe(jobId: string): void {
    this.subscribers.delete(jobId);
  }

  saveJob(jobId: string, jobData: JobData): void {
    const key = `generation_job_${jobId}`;
    localStorage.setItem(key, JSON.stringify(jobData));
  }

  getJob(jobId: string): JobData | null {
    const key = `generation_job_${jobId}`;
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : null;
  }

  clearJob(jobId: string): void {
    const key = `generation_job_${jobId}`;
    localStorage.removeItem(key);
  }

  notifySubscribers(jobId: string, data: any): void {
    const subscriber = this.subscribers.get(jobId);
    if (subscriber) {
      subscriber(data);
    }
  }
}

// ====== API UTILITIES ======

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = config.API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  getBaseUrl(): string {
    return this.baseUrl;
  }

  private getCookie(name: string): string | null {
    if (typeof document === 'undefined') return null;
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop()!.split(';').shift() || null;
    return null;
  }

  private async request(endpoint: string, options: RequestInit = {}): Promise<any> {
    const url = `${this.baseUrl}${endpoint}`;
    const method = (options.method || 'GET').toUpperCase();
    const isUnsafe = !['GET', 'HEAD', 'OPTIONS'].includes(method);
    const csrf = this.getCookie('csrftoken');
    const baseHeaders: Record<string, string> = {
      ...(options.headers as any),
    };
    // Only set JSON content type if body isn't FormData
    const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
    if (!isFormData) {
      baseHeaders['Content-Type'] = baseHeaders['Content-Type'] || 'application/json';
    }
    if (isUnsafe && csrf) {
      baseHeaders['X-CSRFToken'] = csrf;
    }

    const response = await fetch(url, {
      credentials: 'include',
      headers: baseHeaders,
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`);
    }

    return response.json();
  }

  async get(endpoint: string): Promise<any> {
    return this.request(endpoint);
  }

  async post(endpoint: string, data?: any): Promise<any> {
    // Respect FormData bodies
    if (typeof FormData !== 'undefined' && data instanceof FormData) {
      return this.request(endpoint, { method: 'POST', body: data });
    }
    return this.request(endpoint, { method: 'POST', body: data ? JSON.stringify(data) : null });
  }

  async put(endpoint: string, data?: any): Promise<any> {
    return this.request(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : null,
    });
  }

  async delete(endpoint: string): Promise<any> {
    return this.request(endpoint, {
      method: 'DELETE',
    });
  }

  async downloadFile(endpoint: string): Promise<Blob> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, { credentials: 'include' });
    
    if (!response.ok) {
      throw new Error(`Download failed: ${response.statusText}`);
    }
    
    return response.blob();
  }
}

// ====== GENERATION HOOKS ======

export const useGenerationState = (initialConfig = {}) => {
  const [state, setState] = useState(GenerationState.IDLE);
  const [progress, setProgress] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState(initialConfig);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);

  const startGeneration = useCallback((jobId: string) => {
    setState(GenerationState.GENERATING);
    setProgress('');
    setError(null);
    setCurrentJobId(jobId);
  }, []);

  const updateProgress = useCallback((progressMessage: string) => {
    setProgress(progressMessage);
  }, []);

  const completeGeneration = useCallback(() => {
    setState(GenerationState.COMPLETED);
    setProgress('');
    setCurrentJobId(null);
  }, []);

  const failGeneration = useCallback((errorMessage: string) => {
    setState(GenerationState.FAILED);
    setError(errorMessage);
    setProgress('');
    setCurrentJobId(null);
  }, []);

  const cancelGeneration = useCallback(() => {
    setState(GenerationState.CANCELLED);
    setError('Cancelled by user');
    setProgress('');
    setCurrentJobId(null);
  }, []);

  const resetState = useCallback(() => {
    setState(GenerationState.IDLE);
    setProgress('');
    setError(null);
    setCurrentJobId(null);
  }, []);

  const updateConfig = useCallback((updates: any) => {
    setConfig(prev => ({ ...prev, ...updates }));
  }, []);

  return {
    // State
    state,
    progress,
    error,
    config,
    currentJobId,
    
    // Computed state
    isGenerating: state === GenerationState.GENERATING,
    isCompleted: state === GenerationState.COMPLETED,
    isFailed: state === GenerationState.FAILED,
    isCancelled: state === GenerationState.CANCELLED,
    isIdle: state === GenerationState.IDLE,
    
    // Actions
    startGeneration,
    updateProgress,
    completeGeneration,
    failGeneration,
    cancelGeneration,
    resetState,
    updateConfig
  };
};


// ====== UTILITY FUNCTIONS ======

export const createFormData = (config: any): FormData => {
  const formData = new FormData();
  
  Object.keys(config).forEach(key => {
    if (config[key] !== undefined && config[key] !== null) {
      if (Array.isArray(config[key])) {
        config[key].forEach((item: any) => {
          formData.append(key, item);
        });
      } else {
        formData.append(key, config[key]);
      }
    }
  });
  
  return formData;
};

export const downloadFile = async (fileId: string, filename: string, notebookId: string, type: 'report' | 'podcast'): Promise<void> => {
  try {
    const endpoint = type === 'report'
      ? `/reports/${fileId}/download/`
      : `/podcasts/${fileId}/download-audio/`;
    
    const blob = await new ApiClient().downloadFile(endpoint);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Download failed:', error);
    throw error;
  }
}; 
