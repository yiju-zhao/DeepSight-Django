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