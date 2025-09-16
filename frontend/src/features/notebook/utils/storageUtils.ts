/**
 * Simple storage utilities for notebook features
 */

export interface SecureBlobResult {
  url: string;
  revoke: () => void;
  blob: Blob;
}

/**
 * Creates a simple blob URL
 */
export function createSecureBlob(
  data: BlobPart | BlobPart[],
  options: { type?: string } = {}
): SecureBlobResult {
  const blobParts = Array.isArray(data) ? data : [data];
  const blob = new Blob(blobParts, { type: options.type });
  const url = URL.createObjectURL(blob);

  return {
    url,
    blob,
    revoke: () => URL.revokeObjectURL(url)
  };
}

/**
 * Downloads a file securely with authentication
 */
export async function downloadFileSecurely(
  url: string,
  filename: string = 'download'
): Promise<void> {
  const response = await fetch(url, { credentials: 'include' });

  if (!response.ok) {
    throw new Error(`Download failed: ${response.status} ${response.statusText}`);
  }

  const blob = await response.blob();
  const result = createSecureBlob([blob]);

  try {
    const link = document.createElement('a');
    link.href = result.url;
    link.download = filename;
    link.style.display = 'none';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } finally {
    result.revoke();
  }
}

/**
 * Simple blob manager for tracking and cleanup
 */
export function createBlobManager() {
  const activeUrls: string[] = [];

  return {
    create: (data: BlobPart | BlobPart[], options?: { type?: string }) => {
      const result = createSecureBlob(data, options);
      activeUrls.push(result.url);
      return result;
    },

    cleanup: () => {
      activeUrls.forEach(url => {
        if (url.startsWith('blob:')) {
          try {
            URL.revokeObjectURL(url);
          } catch (error) {
            console.debug('Failed to revoke blob URL:', url);
          }
        }
      });
      activeUrls.length = 0;
    },

    getActiveCount: () => activeUrls.length
  };
}