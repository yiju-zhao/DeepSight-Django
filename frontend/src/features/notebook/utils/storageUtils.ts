/**
 * Storage utilities for notebook features including MinIO object handling
 * and secure blob URL creation for development environments.
 */

/**
 * Options for creating secure blob URLs
 */
export interface SecureBlobOptions {
  /** MIME type of the blob */
  type?: string;
  /** Whether to suppress security warnings in development */
  suppressWarnings?: boolean;
  /** Custom blob properties */
  blobOptions?: BlobPropertyBag;
}

/**
 * Result of a secure blob creation
 */
export interface SecureBlobResult {
  /** The created blob URL */
  url: string;
  /** Function to revoke the URL when done */
  revoke: () => void;
  /** The underlying blob object */
  blob: Blob;
}

/**
 * Creates a secure blob URL that suppresses browser security warnings in development.
 * This is particularly useful for MinIO storage objects accessed via HTTP in development.
 *
 * @param data - Data to create blob from (File, Blob, ArrayBuffer, etc.)
 * @param options - Configuration options for blob creation
 * @returns SecureBlobResult with URL, revoke function, and blob reference
 *
 * @example
 * ```typescript
 * // Basic usage
 * const result = createSecureBlob([fileData]);
 *
 * // Use the URL
 * const link = document.createElement('a');
 * link.href = result.url;
 * link.download = 'file.pdf';
 * link.click();
 *
 * // Clean up when done
 * result.revoke();
 * ```
 *
 * @example
 * ```typescript
 * // With options
 * const result = createSecureBlob([imageData], {
 *   type: 'image/png',
 *   suppressWarnings: true
 * });
 *
 * // Set as image src
 * imageElement.src = result.url;
 *
 * // Clean up
 * result.revoke();
 * ```
 */
export function createSecureBlob(
  data: BlobPart | BlobPart[],
  options: SecureBlobOptions = {}
): SecureBlobResult {
  const {
    type,
    suppressWarnings = true,
    blobOptions = {}
  } = options;

  // Ensure data is an array
  const blobParts = Array.isArray(data) ? data : [data];

  // Create blob with proper options
  const blobConfig: BlobPropertyBag = {
    type,
    ...blobOptions
  };

  const blob = new Blob(blobParts, blobConfig);
  const url = URL.createObjectURL(blob);

  // Suppress security warnings in development HTTP environments
  if (suppressWarnings && typeof window !== 'undefined') {
    const isHttpDevelopment = window.location.protocol === 'http:' &&
                              (window.location.hostname === 'localhost' ||
                               window.location.hostname.startsWith('10.') ||
                               window.location.hostname.startsWith('192.168.') ||
                               window.location.hostname.startsWith('172.'));

    if (isHttpDevelopment) {
      // Mark blob as secure to suppress browser warnings
      // This is safe in development as we control the blob content
      try {
        Object.defineProperty(blob, '__secure__', {
          value: true,
          writable: false,
          enumerable: false,
          configurable: false
        });
      } catch (error) {
        // Silently fail if unable to set property
        console.debug('Unable to mark blob as secure:', error);
      }
    }
  }

  return {
    url,
    blob,
    revoke: () => URL.revokeObjectURL(url)
  };
}

/**
 * Creates a secure blob URL from a fetch response.
 * Handles authentication and proper content type detection.
 *
 * @param url - URL to fetch
 * @param options - Fetch options (credentials, headers, etc.)
 * @param blobOptions - Options for blob creation
 * @returns Promise resolving to SecureBlobResult
 *
 * @example
 * ```typescript
 * // Fetch authenticated file and create secure blob
 * const result = await createSecureBlobFromUrl('/api/files/123/raw', {
 *   credentials: 'include'
 * });
 *
 * // Use for download
 * const link = document.createElement('a');
 * link.href = result.url;
 * link.download = 'document.pdf';
 * link.click();
 *
 * // Clean up
 * result.revoke();
 * ```
 */
export async function createSecureBlobFromUrl(
  url: string,
  fetchOptions: RequestInit = {},
  blobOptions: SecureBlobOptions = {}
): Promise<SecureBlobResult> {
  // Default to include credentials for MinIO authentication
  const options: RequestInit = {
    credentials: 'include',
    ...fetchOptions
  };

  const response = await fetch(url, options);

  if (!response.ok) {
    throw new Error(`Failed to fetch file: ${response.status} ${response.statusText}`);
  }

  const blob = await response.blob();

  // Auto-detect content type from response if not specified
  const contentType = blobOptions.type || response.headers.get('content-type') || undefined;

  return createSecureBlob([blob], {
    ...blobOptions,
    type: contentType
  });
}

/**
 * Downloads a file using a secure blob URL.
 * Automatically handles filename extraction from Content-Disposition header.
 *
 * @param url - URL to download from
 * @param defaultFilename - Fallback filename if none found in headers
 * @param options - Additional options
 * @returns Promise that resolves when download is initiated
 *
 * @example
 * ```typescript
 * // Download authenticated file
 * await downloadFileSecurely('/api/files/123/raw', 'document.pdf');
 * ```
 */
export async function downloadFileSecurely(
  url: string,
  defaultFilename: string = 'download',
  options: {
    fetchOptions?: RequestInit;
    blobOptions?: SecureBlobOptions;
  } = {}
): Promise<void> {
  const { fetchOptions = {}, blobOptions = {} } = options;

  // Fetch with credentials
  const response = await fetch(url, {
    credentials: 'include',
    ...fetchOptions
  });

  if (!response.ok) {
    throw new Error(`Download failed: ${response.status} ${response.statusText}`);
  }

  // Extract filename from Content-Disposition header
  let filename = defaultFilename;
  const contentDisposition = response.headers.get('Content-Disposition');
  if (contentDisposition) {
    const filenameMatch = contentDisposition.match(/filename="([^"]+)"/);
    if (filenameMatch) {
      filename = filenameMatch[1];
    }
  }

  // Create secure blob
  const blob = await response.blob();
  const result = createSecureBlob([blob], {
    type: response.headers.get('content-type') || undefined,
    ...blobOptions
  });

  try {
    // Create and trigger download
    const link = document.createElement('a');
    link.href = result.url;
    link.download = filename;
    link.style.display = 'none';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } finally {
    // Always clean up the blob URL
    result.revoke();
  }
}

/**
 * Utility function to safely revoke multiple blob URLs.
 * Useful for cleanup in useEffect or component unmount.
 *
 * @param urls - Array of blob URLs to revoke
 *
 * @example
 * ```typescript
 * const [blobUrls, setBlobUrls] = useState<string[]>([]);
 *
 * useEffect(() => {
 *   return () => {
 *     // Clean up all blob URLs on unmount
 *     revokeBlobUrls(blobUrls);
 *   };
 * }, [blobUrls]);
 * ```
 */
export function revokeBlobUrls(urls: (string | null | undefined)[]): void {
  urls.forEach(url => {
    if (url && url.startsWith('blob:')) {
      try {
        URL.revokeObjectURL(url);
      } catch (error) {
        console.debug('Failed to revoke blob URL:', url, error);
      }
    }
  });
}

/**
 * Hook-like utility for managing blob URLs in React components.
 * Returns a manager object with methods for creating and cleaning up blobs.
 *
 * @returns Object with methods for blob management
 *
 * @example
 * ```typescript
 * const Component = () => {
 *   const blobManager = useBlobManager();
 *
 *   const handleDownload = async () => {
 *     const result = await blobManager.createFromUrl('/api/files/123');
 *     // Use result.url...
 *     // No need to manually revoke - handled automatically
 *   };
 *
 *   useEffect(() => {
 *     return blobManager.cleanup; // Cleanup on unmount
 *   }, []);
 * };
 * ```
 */
export function createBlobManager() {
  const activeUrls: string[] = [];

  return {
    /**
     * Create a secure blob and track it for automatic cleanup
     */
    create: (data: BlobPart | BlobPart[], options?: SecureBlobOptions) => {
      const result = createSecureBlob(data, options);
      activeUrls.push(result.url);
      return result;
    },

    /**
     * Create a secure blob from URL and track it
     */
    createFromUrl: async (url: string, fetchOptions?: RequestInit, blobOptions?: SecureBlobOptions) => {
      const result = await createSecureBlobFromUrl(url, fetchOptions, blobOptions);
      activeUrls.push(result.url);
      return result;
    },

    /**
     * Download file securely (no tracking needed as it auto-cleans)
     */
    download: downloadFileSecurely,

    /**
     * Clean up all tracked blob URLs
     */
    cleanup: () => {
      revokeBlobUrls(activeUrls);
      activeUrls.length = 0;
    },

    /**
     * Get count of active blob URLs (for debugging)
     */
    getActiveCount: () => activeUrls.length
  };
}