import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { apiClient } from '../api'; // Import the existing robust API client

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

/**
 * @deprecated This function is now a wrapper around the existing `apiClient.get` method.
 * Please consider using `apiClient.get` directly for new features.
 */
export async function fetchJson<T = any>(url: string): Promise<T> {
  // Use the existing robust API client that handles CSRF and credentials
  return apiClient.get<T>(url);
}

/**
 * Frontend text processing utilities
 */

export function splitCommaValues(text: string | null | undefined): string[] {
  if (!text) return [];
  return text.split(',')
    .map(item => item.trim())
    .filter(item => item.length > 0);
}

export function splitSemicolonValues(text: string | null | undefined): string[] {
  if (!text) return [];
  return text.split(';')
    .map(item => item.trim())
    .filter(item => item.length > 0);
}

export function formatTruncatedList(
  items: string[],
  maxItems: number = 3,
  separator: string = ', '
): { displayText: string; displayItems: string[]; hasMore: boolean; remainingCount: number } {
  if (items.length === 0) {
    return { displayText: '', displayItems: [], hasMore: false, remainingCount: 0 };
  }

  const displayed = items.slice(0, maxItems);
  const hasMore = items.length > maxItems;
  const remainingCount = Math.max(0, items.length - maxItems);

  return {
    displayText: displayed.join(separator),
    displayItems: displayed,
    hasMore,
    remainingCount
  };
}