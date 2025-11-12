/**
 * useFavorites Hook
 *
 * Manages favorited publications with localStorage persistence.
 * Provides methods to add, remove, check, and retrieve favorite publications.
 *
 * Features:
 * - localStorage persistence
 * - Automatic sync across tabs
 * - Type-safe operations
 * - Performance optimized with Set for lookups
 */

import { useState, useEffect, useCallback } from 'react';
import { Publication } from '../types';

// ============================================================================
// CONSTANTS
// ============================================================================

const STORAGE_KEY = 'deepsight_favorite_publications';
const STORAGE_VERSION = '1.0';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

interface FavoriteData {
  version: string;
  favorites: string[]; // Array of publication IDs
  lastUpdated: string;
}

interface UseFavoritesReturn {
  favorites: Set<string>;
  isFavorite: (publicationId: string) => boolean;
  toggleFavorite: (publicationId: string) => void;
  addFavorite: (publicationId: string) => void;
  removeFavorite: (publicationId: string) => void;
  clearFavorites: () => void;
  favoriteCount: number;
  getFavoritePublications: (publications: Publication[]) => Publication[];
}

// ============================================================================
// STORAGE UTILITIES
// ============================================================================

/**
 * Load favorites from localStorage
 */
function loadFavorites(): Set<string> {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return new Set();

    const data: FavoriteData = JSON.parse(stored);

    // Version check
    if (data.version !== STORAGE_VERSION) {
      console.warn('Favorite data version mismatch, clearing favorites');
      return new Set();
    }

    return new Set(data.favorites);
  } catch (error) {
    console.error('Failed to load favorites:', error);
    return new Set();
  }
}

/**
 * Save favorites to localStorage
 */
function saveFavorites(favorites: Set<string>): void {
  try {
    const data: FavoriteData = {
      version: STORAGE_VERSION,
      favorites: Array.from(favorites),
      lastUpdated: new Date().toISOString(),
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch (error) {
    console.error('Failed to save favorites:', error);
    // Handle quota exceeded error
    if (error instanceof DOMException && error.name === 'QuotaExceededError') {
      console.warn('localStorage quota exceeded, favorites not saved');
    }
  }
}

// ============================================================================
// HOOK
// ============================================================================

/**
 * Hook for managing favorite publications
 */
export function useFavorites(): UseFavoritesReturn {
  const [favorites, setFavorites] = useState<Set<string>>(() => loadFavorites());

  // Persist favorites when they change
  useEffect(() => {
    saveFavorites(favorites);
  }, [favorites]);

  // Sync favorites across tabs
  useEffect(() => {
    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) {
        setFavorites(loadFavorites());
      }
    };

    window.addEventListener('storage', handleStorageChange);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  /**
   * Check if a publication is favorited
   */
  const isFavorite = useCallback(
    (publicationId: string): boolean => {
      return favorites.has(publicationId);
    },
    [favorites]
  );

  /**
   * Add a publication to favorites
   */
  const addFavorite = useCallback((publicationId: string): void => {
    setFavorites((prev) => {
      if (prev.has(publicationId)) return prev;
      const next = new Set(prev);
      next.add(publicationId);
      return next;
    });
  }, []);

  /**
   * Remove a publication from favorites
   */
  const removeFavorite = useCallback((publicationId: string): void => {
    setFavorites((prev) => {
      if (!prev.has(publicationId)) return prev;
      const next = new Set(prev);
      next.delete(publicationId);
      return next;
    });
  }, []);

  /**
   * Toggle favorite status
   */
  const toggleFavorite = useCallback(
    (publicationId: string): void => {
      if (isFavorite(publicationId)) {
        removeFavorite(publicationId);
      } else {
        addFavorite(publicationId);
      }
    },
    [isFavorite, addFavorite, removeFavorite]
  );

  /**
   * Clear all favorites
   */
  const clearFavorites = useCallback((): void => {
    setFavorites(new Set());
  }, []);

  /**
   * Filter publications to only favorites
   */
  const getFavoritePublications = useCallback(
    (publications: Publication[]): Publication[] => {
      return publications.filter((pub) => favorites.has(pub.id));
    },
    [favorites]
  );

  return {
    favorites,
    isFavorite,
    toggleFavorite,
    addFavorite,
    removeFavorite,
    clearFavorites,
    favoriteCount: favorites.size,
    getFavoritePublications,
  };
}

// ============================================================================
// EXPORT UTILITIES
// ============================================================================

/**
 * Export favorites for backup
 */
export function exportFavorites(): string | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored;
  } catch (error) {
    console.error('Failed to export favorites:', error);
    return null;
  }
}

/**
 * Import favorites from backup
 */
export function importFavorites(data: string): boolean {
  try {
    const parsed: FavoriteData = JSON.parse(data);

    if (!parsed.favorites || !Array.isArray(parsed.favorites)) {
      throw new Error('Invalid favorites data format');
    }

    localStorage.setItem(STORAGE_KEY, data);

    // Trigger storage event for sync
    window.dispatchEvent(
      new StorageEvent('storage', {
        key: STORAGE_KEY,
        newValue: data,
      })
    );

    return true;
  } catch (error) {
    console.error('Failed to import favorites:', error);
    return false;
  }
}

/**
 * Get favorite statistics
 */
export function getFavoriteStats(): {
  count: number;
  lastUpdated: string | null;
} {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      return { count: 0, lastUpdated: null };
    }

    const data: FavoriteData = JSON.parse(stored);

    return {
      count: data.favorites.length,
      lastUpdated: data.lastUpdated,
    };
  } catch (error) {
    console.error('Failed to get favorite stats:', error);
    return { count: 0, lastUpdated: null };
  }
}

export default useFavorites;
