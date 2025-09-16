# API Client Usage Guide

This document explains how to use the consolidated API client and React Query patterns in the DeepSight application.

## 📡 API Client Overview

The application uses a single, consolidated API client (`src/shared/api/client.ts`) that handles:
- CSRF token management
- Request/response interceptors
- Error handling and parsing
- Base URL configuration
- Authentication headers

## 🔧 Basic API Client Usage

### Import the Client
```typescript
import { apiClient } from '@/shared/api/client';
```

### Making Requests
```typescript
// GET request
const notebooks = await apiClient.get('/api/notebooks/');

// POST request with data
const newNotebook = await apiClient.post('/api/notebooks/', {
  name: 'My Notebook',
  description: 'A sample notebook'
});

// PUT request
const updatedNotebook = await apiClient.put(`/api/notebooks/${id}/`, data);

// DELETE request
await apiClient.delete(`/api/notebooks/${id}/`);
```

### File Uploads
```typescript
const formData = new FormData();
formData.append('file', file);
formData.append('name', 'Source Name');

const response = await apiClient.post('/api/sources/', formData, {
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});
```

### Download Files
```typescript
const response = await apiClient.get(`/api/reports/${id}/download/`, {
  responseType: 'blob',
});

// Create download link
const url = window.URL.createObjectURL(new Blob([response.data]));
const link = document.createElement('a');
link.href = url;
link.setAttribute('download', filename);
document.body.appendChild(link);
link.click();
link.remove();
```

## 🚀 React Query Integration

### Query Keys Structure
All query keys follow a hierarchical structure defined in `src/shared/queries/keys.ts`:

```typescript
export const queryKeys = {
  notebooks: {
    all: ['notebooks'] as const,
    lists: () => [...queryKeys.notebooks.all, 'list'] as const,
    list: (filters?: NotebookFilters) =>
      [...queryKeys.notebooks.lists(), { filters }] as const,
    details: () => [...queryKeys.notebooks.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.notebooks.details(), id] as const,
  },
  reports: {
    all: ['reports'] as const,
    lists: () => [...queryKeys.reports.all, 'list'] as const,
    list: (notebookId?: string, filters?: ReportFilters) =>
      [...queryKeys.reports.lists(), { notebookId, filters }] as const,
    details: () => [...queryKeys.reports.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.reports.details(), id] as const,
  },
};
```

### Query Hooks

#### Basic Query
```typescript
export function useNotebooks(filters?: NotebookFilters) {
  return useQuery({
    queryKey: queryKeys.notebooks.list(filters),
    queryFn: () => apiClient.get('/api/notebooks/', { params: filters }),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (previously cacheTime)
  });
}
```

#### Query with Auto-refresh
```typescript
export function useReport(jobId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.reports.detail(jobId),
    queryFn: () => apiClient.get(`/api/reports/${jobId}/`),
    enabled: options?.enabled !== false,
    refetchInterval: (data) => {
      // Auto-refresh every 5 seconds for running jobs
      const status = data?.status;
      return ['pending', 'running'].includes(status) ? 5000 : false;
    },
    staleTime: 0, // Always refetch for job status
  });
}
```

#### Dependent Query
```typescript
export function useReportContent(jobId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.reports.content(jobId),
    queryFn: () => apiClient.get(`/api/reports/${jobId}/content/`),
    enabled: options?.enabled !== false && !!jobId,
    staleTime: 30 * 60 * 1000, // Content doesn't change often
  });
}
```

### Mutation Hooks

#### Basic Mutation with Optimistic Updates
```typescript
export function useCreateNotebook() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateNotebookRequest) =>
      apiClient.post('/api/notebooks/', data),

    onMutate: async (newNotebook) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({
        queryKey: queryKeys.notebooks.lists()
      });

      // Snapshot previous value
      const previousNotebooks = queryClient.getQueryData(
        queryKeys.notebooks.list()
      );

      // Optimistically update
      queryClient.setQueryData(
        queryKeys.notebooks.list(),
        (old: Notebook[] = []) => [
          { id: 'temp-' + Date.now(), ...newNotebook, status: 'creating' },
          ...old,
        ]
      );

      return { previousNotebooks };
    },

    onError: (err, newNotebook, context) => {
      // Rollback on error
      queryClient.setQueryData(
        queryKeys.notebooks.list(),
        context?.previousNotebooks
      );
    },

    onSettled: () => {
      // Always refetch after mutation
      queryClient.invalidateQueries({
        queryKey: queryKeys.notebooks.lists()
      });
    },
  });
}
```

#### Mutation with Toast Notifications
```typescript
import { operationCallbacks } from '@/shared/utils/notifications';

export function useDeleteReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => apiClient.delete(`/api/reports/${id}/`),

    ...operationCallbacks.delete('Report', {
      onSuccess: (data, id) => {
        // Remove from cache
        queryClient.setQueryData(
          queryKeys.reports.list(),
          (old: Report[] = []) => old.filter(report => report.id !== id)
        );

        // Invalidate related queries
        queryClient.invalidateQueries({
          queryKey: queryKeys.reports.lists()
        });
      }
    }),
  });
}
```

## 🎯 Advanced Patterns

### Infinite Queries
```typescript
export function useNotebooksInfinite(filters?: NotebookFilters) {
  return useInfiniteQuery({
    queryKey: queryKeys.notebooks.list(filters),
    queryFn: ({ pageParam = 1 }) =>
      apiClient.get('/api/notebooks/', {
        params: { ...filters, page: pageParam }
      }),
    getNextPageParam: (lastPage) => {
      const { hasNext, page } = lastPage.meta.pagination;
      return hasNext ? page + 1 : undefined;
    },
    staleTime: 5 * 60 * 1000,
  });
}
```

### Background Sync
```typescript
export function useReportsWithSync(notebookId?: string) {
  return useQuery({
    queryKey: queryKeys.reports.list(notebookId),
    queryFn: () => apiClient.get('/api/reports/', {
      params: { notebook_id: notebookId }
    }),
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
    refetchInterval: 30 * 1000, // Background refresh every 30 seconds
  });
}
```

### Cache Utilities
```typescript
export function useReportsUtils() {
  const queryClient = useQueryClient();

  return {
    // Prefetch reports for a notebook
    prefetchReports: (notebookId: string) => {
      return queryClient.prefetchQuery({
        queryKey: queryKeys.reports.list(notebookId),
        queryFn: () => apiClient.get('/api/reports/', {
          params: { notebook_id: notebookId }
        }),
        staleTime: 5 * 60 * 1000,
      });
    },

    // Invalidate all reports
    invalidateReports: () => {
      return queryClient.invalidateQueries({
        queryKey: queryKeys.reports.all
      });
    },

    // Set report in cache
    setReport: (report: Report) => {
      queryClient.setQueryData(
        queryKeys.reports.detail(report.id),
        report
      );
    },

    // Remove report from cache
    removeReport: (id: string) => {
      queryClient.removeQueries({
        queryKey: queryKeys.reports.detail(id)
      });
    },
  };
}
```

## 🎨 Component Integration

### Using Queries in Components
```typescript
import { useNotebooks, useCreateNotebook } from '@/features/notebook/hooks';

function NotebookList() {
  const {
    data: notebooks = [],
    isLoading,
    error,
    refetch
  } = useNotebooks();

  const createNotebook = useCreateNotebook();

  const handleCreate = async (data: CreateNotebookRequest) => {
    try {
      await createNotebook.mutateAsync(data);
      // Success notification handled by mutation
    } catch (error) {
      // Error notification handled by mutation
    }
  };

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} onRetry={refetch} />;

  return (
    <div>
      {notebooks.map(notebook => (
        <NotebookCard key={notebook.id} notebook={notebook} />
      ))}
      <CreateButton onClick={() => setShowCreateModal(true)} />
    </div>
  );
}
```

### Error Boundaries
```typescript
function NotebookFeature() {
  return (
    <ErrorBoundary fallback={<ErrorPage />}>
      <Suspense fallback={<LoadingPage />}>
        <NotebookList />
      </Suspense>
    </ErrorBoundary>
  );
}
```

## 🛡️ Error Handling

### API Error Format
The backend returns consistent error responses:
```typescript
interface ApiError {
  detail: string;
  error_code?: string;
  field_errors?: Record<string, string[]>;
}
```

### Handling Errors in Queries
```typescript
export function useNotebooks() {
  return useQuery({
    queryKey: queryKeys.notebooks.list(),
    queryFn: () => apiClient.get('/api/notebooks/'),
    retry: (failureCount, error) => {
      // Don't retry on 4xx errors
      if (error.response?.status >= 400 && error.response?.status < 500) {
        return false;
      }
      return failureCount < 3;
    },
    retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}
```

### Global Error Handling
```typescript
import { toast } from '@/shared/utils/toast';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      onError: (error) => {
        // Global error handling for queries
        const message = error.response?.data?.detail || 'An error occurred';
        toast.error(message);
      },
    },
    mutations: {
      onError: (error) => {
        // Global error handling for mutations
        const message = error.response?.data?.detail || 'An error occurred';
        toast.error(message);
      },
    },
  },
});
```

## 🔄 Migration from Redux

### Before (Redux Thunk)
```typescript
// Old Redux pattern
const dispatch = useDispatch();
const notebooks = useSelector(selectNotebooks);
const isLoading = useSelector(selectNotebooksLoading);

useEffect(() => {
  dispatch(fetchNotebooks());
}, [dispatch]);
```

### After (React Query)
```typescript
// New React Query pattern
const { data: notebooks = [], isLoading } = useNotebooks();
// That's it! No useEffect needed, automatic caching and background updates
```

## 📋 Best Practices

1. **Use Feature-Scoped Hooks**: Create custom hooks for each feature that encapsulate query logic
2. **Include Filters in Query Keys**: Always include filters and params in query keys to prevent cache collisions
3. **Handle Loading States**: Provide good loading and error states for better UX
4. **Optimistic Updates**: Use optimistic updates for better perceived performance
5. **Background Refetching**: Enable background refetching for real-time data
6. **Error Boundaries**: Wrap components with error boundaries for graceful error handling
7. **Cache Invalidation**: Strategically invalidate cache after mutations
8. **Prefetching**: Prefetch data that users are likely to need

## 🎯 Common Patterns

### Polling for Job Status
```typescript
const { data: job } = useQuery({
  queryKey: ['job', jobId],
  queryFn: () => apiClient.get(`/api/jobs/${jobId}/`),
  refetchInterval: (data) => {
    return ['pending', 'running'].includes(data?.status) ? 1000 : false;
  },
});
```

### Dependent Data Loading
```typescript
const { data: notebook } = useNotebook(notebookId);
const { data: sources } = useSources(notebookId, {
  enabled: !!notebook, // Only fetch sources if notebook exists
});
```

### Optimistic List Updates
```typescript
const createMutation = useMutation({
  mutationFn: createItem,
  onMutate: async (newItem) => {
    await queryClient.cancelQueries(['items']);
    const previousItems = queryClient.getQueryData(['items']);

    queryClient.setQueryData(['items'], old => [...old, newItem]);

    return { previousItems };
  },
  onError: (err, newItem, context) => {
    queryClient.setQueryData(['items'], context.previousItems);
  },
  onSettled: () => {
    queryClient.invalidateQueries(['items']);
  },
});
```

For more examples and patterns, see the existing feature implementations in the codebase.