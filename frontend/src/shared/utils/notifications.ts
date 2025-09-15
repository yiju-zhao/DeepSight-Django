/**
 * Standardized notification utilities for React Query integration
 *
 * Provides consistent toast messages for common operations like
 * create, update, delete, and error handling.
 */

import { toast } from '@/shared/components/ui/use-toast';

export interface NotificationOptions {
  title?: string;
  description?: string;
  duration?: number;
  action?: React.ReactNode;
}

export interface OperationNotificationOptions {
  resourceName: string;
  resourceId?: string;
  customMessages?: {
    loading?: string;
    success?: string;
    error?: string;
  };
}

/**
 * Standard notification messages for common operations
 */
export const notifications = {
  /**
   * Success notifications
   */
  success: {
    created: (resourceName: string, resourceId?: string) =>
      toast({
        title: 'Success',
        description: `${resourceName}${resourceId ? ` ${resourceId}` : ''} created successfully`,
        variant: 'default',
      }),

    updated: (resourceName: string, resourceId?: string) =>
      toast({
        title: 'Success',
        description: `${resourceName}${resourceId ? ` ${resourceId}` : ''} updated successfully`,
        variant: 'default',
      }),

    deleted: (resourceName: string, resourceId?: string) =>
      toast({
        title: 'Success',
        description: `${resourceName}${resourceId ? ` ${resourceId}` : ''} deleted successfully`,
        variant: 'default',
      }),

    saved: (resourceName: string) =>
      toast({
        title: 'Saved',
        description: `${resourceName} has been saved`,
        variant: 'default',
      }),

    copied: (item: string = 'Item') =>
      toast({
        title: 'Copied',
        description: `${item} copied to clipboard`,
        variant: 'default',
      }),

    imported: (count: number, resourceName: string) =>
      toast({
        title: 'Import Complete',
        description: `Successfully imported ${count} ${resourceName}${count !== 1 ? 's' : ''}`,
        variant: 'default',
      }),

    exported: (resourceName: string) =>
      toast({
        title: 'Export Complete',
        description: `${resourceName} exported successfully`,
        variant: 'default',
      }),
  },

  /**
   * Error notifications
   */
  error: {
    create: (resourceName: string, error?: string) =>
      toast({
        title: 'Creation Failed',
        description: error || `Failed to create ${resourceName}`,
        variant: 'destructive',
      }),

    update: (resourceName: string, error?: string) =>
      toast({
        title: 'Update Failed',
        description: error || `Failed to update ${resourceName}`,
        variant: 'destructive',
      }),

    delete: (resourceName: string, error?: string) =>
      toast({
        title: 'Deletion Failed',
        description: error || `Failed to delete ${resourceName}`,
        variant: 'destructive',
      }),

    load: (resourceName: string, error?: string) =>
      toast({
        title: 'Loading Failed',
        description: error || `Failed to load ${resourceName}`,
        variant: 'destructive',
      }),

    network: (message?: string) =>
      toast({
        title: 'Network Error',
        description: message || 'Please check your internet connection and try again',
        variant: 'destructive',
      }),

    validation: (message?: string) =>
      toast({
        title: 'Validation Error',
        description: message || 'Please check your input and try again',
        variant: 'destructive',
      }),

    permission: (action?: string) =>
      toast({
        title: 'Permission Denied',
        description: action ? `You don't have permission to ${action}` : 'You don\'t have permission to perform this action',
        variant: 'destructive',
      }),

    generic: (error?: string | Error) => {
      const message = error instanceof Error ? error.message : error || 'An unexpected error occurred';
      return toast({
        title: 'Error',
        description: message,
        variant: 'destructive',
      });
    },
  },

  /**
   * Info notifications
   */
  info: {
    processing: (resourceName: string, action: string = 'processing') =>
      toast({
        title: 'Processing',
        description: `${resourceName} is ${action}...`,
        variant: 'default',
      }),

    queued: (resourceName: string) =>
      toast({
        title: 'Queued',
        description: `${resourceName} has been queued for processing`,
        variant: 'default',
      }),

    cancelled: (resourceName: string) =>
      toast({
        title: 'Cancelled',
        description: `${resourceName} operation was cancelled`,
        variant: 'default',
      }),

    noChanges: () =>
      toast({
        title: 'No Changes',
        description: 'No changes were made',
        variant: 'default',
      }),

    offline: () =>
      toast({
        title: 'Offline',
        description: 'You are currently offline. Changes will sync when reconnected.',
        variant: 'default',
      }),
  },

  /**
   * Custom notification with full control
   */
  custom: (options: NotificationOptions) =>
    toast({
      title: options.title,
      description: options.description,
      duration: options.duration,
      action: options.action,
      variant: 'default',
    }),
};

/**
 * React Query callback helpers
 * These can be used directly in useMutation onSuccess/onError callbacks
 */
export const createNotificationCallbacks = (options: OperationNotificationOptions) => ({
  onSuccess: () => {
    const message = options.customMessages?.success || `${options.resourceName} operation completed successfully`;
    toast({
      title: 'Success',
      description: message,
      variant: 'default',
    });
  },

  onError: (error: Error) => {
    const message = options.customMessages?.error || error.message || `${options.resourceName} operation failed`;
    toast({
      title: 'Error',
      description: message,
      variant: 'destructive',
    });
  },
});

/**
 * Specific operation callback creators
 */
export const operationCallbacks = {
  create: (resourceName: string, customMessages?: { success?: string; error?: string }) => ({
    onSuccess: () => notifications.success.created(resourceName),
    onError: (error: Error) => notifications.error.create(resourceName, customMessages?.error || error.message),
  }),

  update: (resourceName: string, customMessages?: { success?: string; error?: string }) => ({
    onSuccess: () => notifications.success.updated(resourceName),
    onError: (error: Error) => notifications.error.update(resourceName, customMessages?.error || error.message),
  }),

  delete: (resourceName: string, customMessages?: { success?: string; error?: string }) => ({
    onSuccess: () => notifications.success.deleted(resourceName),
    onError: (error: Error) => notifications.error.delete(resourceName, customMessages?.error || error.message),
  }),
};

/**
 * Loading state helpers
 */
export const loadingStates = {
  show: (message: string) =>
    toast({
      title: 'Loading',
      description: message,
      duration: Infinity, // Keep until manually dismissed
      variant: 'default',
    }),

  hide: () => {
    // Implementation depends on toast library's dismiss method
    // This would need to be implemented based on the specific toast library
  },
};

export default notifications;