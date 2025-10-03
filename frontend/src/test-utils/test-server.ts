/**
 * Mock Service Worker setup for testing
 * Provides API mocking for all tests
 */

import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { config } from "@/config";

// Mock API responses
const mockNotebook = {
  id: '1',
  name: 'Test Notebook',
  description: 'A test notebook',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const mockSource = {
  id: '1',
  notebook_id: '1',
  filename: 'test.pdf',
  ext: 'pdf',
  size: 1024,
  created_at: '2024-01-01T00:00:00Z',
  selected: false,
  parsing_status: 'done',
  metadata: {},
};

const mockUser = {
  id: '1',
  username: 'testuser',
  email: 'test@example.com',
};

// API handlers
const handlers = [
  // Authentication
  http.get(`${config.API_BASE_URL}/users/me/`, () => {
    return HttpResponse.json(mockUser);
  }),

  http.post(`${config.API_BASE_URL}/users/login/`, async ({ request }) => {
    const body = await request.json() as any;
    if (body?.username === 'testuser' && body?.password === 'testpass') {
      return HttpResponse.json(mockUser);
    }
    return HttpResponse.json({ error: 'Invalid credentials' }, { status: 401 });
  }),

  http.post(`${config.API_BASE_URL}/users/logout/`, () => {
    return HttpResponse.json({ success: true });
  }),

  // Notebooks
  http.get(`${config.API_BASE_URL}/notebooks/`, () => {
    return HttpResponse.json([mockNotebook]);
  }),

  http.get(`${config.API_BASE_URL}/notebooks/:id/`, ({ params }) => {
    return HttpResponse.json({ ...mockNotebook, id: params.id });
  }),

  http.post(`${config.API_BASE_URL}/notebooks/`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({ ...mockNotebook, ...(body || {}), id: '2' });
  }),

  http.put(`${config.API_BASE_URL}/notebooks/:id/`, async ({ request, params }) => {
    const body = await request.json() as any;
    return HttpResponse.json({ ...mockNotebook, ...(body || {}), id: params.id });
  }),

  http.delete(`${config.API_BASE_URL}/notebooks/:id/`, () => {
    return HttpResponse.json({ success: true });
  }),

  // Sources
  http.get(`${config.API_BASE_URL}/notebooks/:notebookId/sources/`, () => {
    return HttpResponse.json([mockSource]);
  }),

  http.post(`${config.API_BASE_URL}/notebooks/:notebookId/sources/`, async ({ request, params }) => {
    const body = await request.json() as any;
    return HttpResponse.json({ 
      ...mockSource, 
      ...(body || {}), 
      id: '2', 
      notebook_id: params.notebookId 
    });
  }),

  http.delete(`${config.API_BASE_URL}/notebooks/:notebookId/sources/:sourceId/`, () => {
    return HttpResponse.json({ success: true });
  }),

  // Chat
  http.post(`${config.API_BASE_URL}/notebooks/:notebookId/chat/`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({
      message: `Echo: ${body?.message || ''}`,
      timestamp: new Date().toISOString(),
    });
  }),

  // Reports - Updated to match new API structure
  http.get(`${config.API_BASE_URL}/reports/`, ({ request }) => {
    const url = new URL(request.url);
    const notebook = url.searchParams.get('notebook');

    const mockReports = [
      {
        job_id: 'job-1',
        report_id: 'report-1',
        status: 'completed',
        progress: 'Report generated successfully',
        title: 'Test Report',
        article_title: 'Test Article',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T01:00:00Z',
        has_files: true,
        has_content: true,
        notebook: notebook || '1',
      },
      {
        job_id: 'job-2',
        report_id: 'report-2',
        status: 'running',
        progress: 'Generating outline...',
        title: 'Running Report',
        article_title: 'Running Article',
        created_at: '2024-01-01T02:00:00Z',
        updated_at: '2024-01-01T02:30:00Z',
        has_files: false,
        has_content: false,
        notebook: notebook || '1',
      }
    ];

    const filteredReports = notebook
      ? mockReports.filter(r => r.notebook === notebook)
      : mockReports;

    return HttpResponse.json({ reports: filteredReports });
  }),

  http.get(`${config.API_BASE_URL}/reports/:jobId/`, ({ params }) => {
    return HttpResponse.json({
      job_id: params.jobId,
      report_id: `report-${params.jobId}`,
      status: params.jobId === 'job-1' ? 'completed' : 'running',
      progress: params.jobId === 'job-1' ? 'Completed' : 'Processing...',
      title: 'Test Report',
      article_title: 'Test Article',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T01:00:00Z',
      has_files: true,
      has_content: true,
    });
  }),

  http.get(`${config.API_BASE_URL}/reports/:jobId/content/`, ({ params }) => {
    return HttpResponse.json({
      job_id: params.jobId,
      report_id: `report-${params.jobId}`,
      content: '# Test Report\n\nThis is a test report content.',
      article_title: 'Test Article',
      generated_files: ['report.pdf', 'summary.docx'],
    });
  }),

  http.post(`${config.API_BASE_URL}/reports/`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({
      job_id: 'job-new',
      report_id: 'report-new',
      status: 'pending',
      message: 'Report generation started',
    });
  }),

  http.put(`${config.API_BASE_URL}/reports/:jobId/`, async ({ request, params }) => {
    const body = await request.json() as any;
    return HttpResponse.json({
      job_id: params.jobId,
      status: 'completed',
      updated_at: new Date().toISOString(),
    });
  }),

  http.delete(`${config.API_BASE_URL}/reports/:jobId/`, ({ params }) => {
    return HttpResponse.json({ success: true });
  }),

  http.post(`${config.API_BASE_URL}/reports/:jobId/cancel/`, ({ params }) => {
    return HttpResponse.json({
      job_id: params.jobId,
      status: 'cancelled',
      message: 'Report generation cancelled',
    });
  }),

  http.get(`${config.API_BASE_URL}/reports/models/`, () => {
    return HttpResponse.json({
      providers: ['openai', 'google'],
      retrievers: ['tavily', 'brave', 'searxng'],
      time_ranges: ['ALL', 'day', 'week', 'month', 'year'],
    });
  }),

  // Podcasts
  http.get(`${config.API_BASE_URL}/notebooks/:notebookId/podcasts/`, () => {
    return HttpResponse.json([{
      id: '1',
      title: 'Test Podcast',
      status: 'completed',
      audioUrl: 'https://example.com/audio.mp3',
      created_at: '2024-01-01T00:00:00Z',
    }]);
  }),

  http.post(`${config.API_BASE_URL}/notebooks/:notebookId/podcasts/`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({
      id: '2',
      ...(body || {}),
      status: 'pending',
      created_at: new Date().toISOString(),
    });
  }),

  // Error handlers
  http.get('*/error/500', () => {
    return HttpResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }),

  http.get('*/error/404', () => {
    return HttpResponse.json({ error: 'Not Found' }, { status: 404 });
  }),
];

// Create server
export const server = setupServer(...handlers);

// Helper functions for tests
export const mockApiResponse = (endpoint: string, response: any, status = 200) => {
  server.use(
    http.get(endpoint, () => {
      return HttpResponse.json(response, { status });
    })
  );
};

export const mockApiError = (endpoint: string, status = 500, message = 'Server Error') => {
  server.use(
    http.get(endpoint, () => {
      return HttpResponse.json({ error: message }, { status });
    })
  );
};

// Test data factories
export const createMockNotebook = (overrides = {}) => ({
  ...mockNotebook,
  ...overrides,
});

export const createMockSource = (overrides = {}) => ({
  ...mockSource,
  ...overrides,
});

export const createMockUser = (overrides = {}) => ({
  ...mockUser,
  ...overrides,
});
