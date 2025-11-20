import React from 'react';
import { PodcastFilters as PodcastFiltersType } from '../types/type';

interface PodcastFiltersProps {
  filters: PodcastFiltersType;
  onFiltersChange: (filters: PodcastFiltersType) => void;
}

const PodcastFilters: React.FC<PodcastFiltersProps> = ({
  filters,
  onFiltersChange
}) => {
  const handleFilterChange = (key: keyof PodcastFiltersType, value: any) => {
    onFiltersChange({
      ...filters,
      [key]: value
    });
  };

  const clearFilters = () => {
    onFiltersChange({});
  };

  const hasActiveFilters = Object.keys(filters).some(key => filters[key as keyof PodcastFiltersType]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">Filters</h3>
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="text-sm text-purple-600 hover:text-purple-800"
          >
            Clear all filters
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Date Range Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Date Range
          </label>
          <div className="flex space-x-2">
            <input
              type="date"
              value={filters.date_range?.start || ''}
              onChange={(e) => handleFilterChange('date_range', {
                ...filters.date_range,
                start: e.target.value
              })}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
            <input
              type="date"
              value={filters.date_range?.end || ''}
              onChange={(e) => handleFilterChange('date_range', {
                ...filters.date_range,
                end: e.target.value
              })}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default PodcastFilters; 
