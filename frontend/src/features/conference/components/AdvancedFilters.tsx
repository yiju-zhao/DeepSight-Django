/**
 * Advanced Filters Component
 *
 * Provides sophisticated filtering capabilities for publications:
 * - Multi-select filters (countries, organizations, topics)
 * - Rating range slider
 * - Keyword tag filtering
 * - Filter chips with quick remove
 * - Save/reset filter presets
 */

import { useState, useMemo, useEffect } from 'react';
import {
  Filter,
  X,
  ChevronDown,
  Star,
  Building2,
  Globe,
  Tag,
  RotateCcw,
  Bookmark,
} from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import { Card, CardContent, CardHeader } from '@/shared/components/ui/card';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/shared/components/ui/popover';
import { Checkbox } from '@/shared/components/ui/checkbox';
import { Separator } from '@/shared/components/ui/separator';
import { Badge } from '@/shared/components/ui/badge';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export interface FilterState {
  countries: string[];
  organizations: string[];
  topics: string[];
  keywords: string[];
  ratingRange: [number, number];
}

export interface FilterOptions {
  countries: string[];
  organizations: string[];
  topics: string[];
  keywords: string[];
}

interface AdvancedFiltersProps {
  options: FilterOptions;
  filters: FilterState;
  onFiltersChange: (filters: FilterState) => void;
  isLoading?: boolean;
}

// ============================================================================
// FILTER CHIPS
// ============================================================================

interface FilterChipsProps {
  filters: FilterState;
  onRemove: (type: keyof FilterState, value: string | null) => void;
  onReset: () => void;
}

const FilterChips = ({ filters, onRemove, onReset }: FilterChipsProps) => {
  const hasFilters = useMemo(() => {
    return (
      filters.countries.length > 0 ||
      filters.organizations.length > 0 ||
      filters.topics.length > 0 ||
      filters.keywords.length > 0 ||
      filters.ratingRange[0] > 0 ||
      filters.ratingRange[1] < 10
    );
  }, [filters]);

  if (!hasFilters) return null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-sm font-medium text-muted-foreground">Active filters:</span>

      {/* Country chips */}
      {filters.countries.map((country) => (
        <Badge key={country} variant="secondary" className="gap-1">
          <Globe className="h-3 w-3" />
          {country}
          <button
            onClick={() => onRemove('countries', country)}
            className="ml-1 hover:bg-destructive/20 rounded-full p-0.5"
          >
            <X className="h-3 w-3" />
          </button>
        </Badge>
      ))}

      {/* Organization chips */}
      {filters.organizations.map((org) => (
        <Badge key={org} variant="secondary" className="gap-1">
          <Building2 className="h-3 w-3" />
          {org}
          <button
            onClick={() => onRemove('organizations', org)}
            className="ml-1 hover:bg-destructive/20 rounded-full p-0.5"
          >
            <X className="h-3 w-3" />
          </button>
        </Badge>
      ))}

      {/* Topic chips */}
      {filters.topics.map((topic) => (
        <Badge key={topic} variant="secondary" className="gap-1">
          <Tag className="h-3 w-3" />
          {topic}
          <button
            onClick={() => onRemove('topics', topic)}
            className="ml-1 hover:bg-destructive/20 rounded-full p-0.5"
          >
            <X className="h-3 w-3" />
          </button>
        </Badge>
      ))}

      {/* Keyword chips */}
      {filters.keywords.map((keyword) => (
        <Badge key={keyword} variant="secondary" className="gap-1">
          {keyword}
          <button
            onClick={() => onRemove('keywords', keyword)}
            className="ml-1 hover:bg-destructive/20 rounded-full p-0.5"
          >
            <X className="h-3 w-3" />
          </button>
        </Badge>
      ))}

      {/* Rating range chip */}
      {(filters.ratingRange[0] > 0 || filters.ratingRange[1] < 10) && (
        <Badge variant="secondary" className="gap-1">
          <Star className="h-3 w-3" />
          {filters.ratingRange[0].toFixed(1)} - {filters.ratingRange[1].toFixed(1)}
          <button
            onClick={() => onRemove('ratingRange', null)}
            className="ml-1 hover:bg-destructive/20 rounded-full p-0.5"
          >
            <X className="h-3 w-3" />
          </button>
        </Badge>
      )}

      {/* Reset all button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={onReset}
        className="h-7 gap-1 text-xs"
      >
        <RotateCcw className="h-3 w-3" />
        Reset all
      </Button>
    </div>
  );
};

// ============================================================================
// MULTI-SELECT FILTER
// ============================================================================

interface MultiSelectFilterProps {
  label: string;
  icon: React.ElementType;
  options: string[];
  selected: string[];
  onSelectionChange: (selected: string[]) => void;
  maxDisplay?: number;
}

const MultiSelectFilter = ({
  label,
  icon: Icon,
  options,
  selected,
  onSelectionChange,
  maxDisplay = 10,
}: MultiSelectFilterProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredOptions = useMemo(() => {
    return options.filter((option) =>
      option.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [options, searchTerm]);

  const displayOptions = useMemo(() => {
    return filteredOptions.slice(0, maxDisplay);
  }, [filteredOptions, maxDisplay]);

  const toggleOption = (option: string) => {
    if (selected.includes(option)) {
      onSelectionChange(selected.filter((s) => s !== option));
    } else {
      onSelectionChange([...selected, option]);
    }
  };

  const toggleAll = () => {
    if (selected.length === filteredOptions.length) {
      onSelectionChange([]);
    } else {
      onSelectionChange(filteredOptions);
    }
  };

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
        >
          <Icon className="h-4 w-4" />
          {label}
          {selected.length > 0 && (
            <Badge variant="secondary" className="ml-1 px-1.5 py-0">
              {selected.length}
            </Badge>
          )}
          <ChevronDown className="h-4 w-4 opacity-50" />
        </Button>
      </PopoverTrigger>

      <PopoverContent className="w-72 p-0" align="start">
        <div className="p-3 border-b">
          <input
            type="text"
            placeholder={`Search ${label.toLowerCase()}...`}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-3 py-2 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div className="p-2">
          <div className="flex items-center justify-between mb-2 px-2">
            <span className="text-xs text-muted-foreground">
              {selected.length} of {filteredOptions.length} selected
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleAll}
              className="h-7 text-xs"
            >
              {selected.length === filteredOptions.length ? 'Clear' : 'Select all'}
            </Button>
          </div>

          <Separator className="my-2" />

          <div className="max-h-64 overflow-y-auto space-y-1">
            {displayOptions.map((option) => (
              <label
                key={option}
                className="flex items-center gap-2 px-2 py-2 rounded-md hover:bg-accent cursor-pointer"
              >
                <Checkbox
                  checked={selected.includes(option)}
                  onCheckedChange={() => toggleOption(option)}
                />
                <span className="text-sm flex-1">{option}</span>
              </label>
            ))}

            {filteredOptions.length > maxDisplay && (
              <div className="px-2 py-2 text-xs text-muted-foreground text-center">
                +{filteredOptions.length - maxDisplay} more options
              </div>
            )}

            {filteredOptions.length === 0 && (
              <div className="px-2 py-4 text-sm text-muted-foreground text-center">
                No options found
              </div>
            )}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
};

// ============================================================================
// RATING RANGE SLIDER
// ============================================================================

interface RatingRangeSliderProps {
  value: [number, number];
  onChange: (value: [number, number]) => void;
}

const RatingRangeSlider = ({ value, onChange }: RatingRangeSliderProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [localValue, setLocalValue] = useState<[number, number]>(value);

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  const handleApply = () => {
    onChange(localValue);
    setIsOpen(false);
  };

  const hasCustomRange = value[0] > 0 || value[1] < 10;

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
        >
          <Star className="h-4 w-4" />
          Rating
          {hasCustomRange && (
            <Badge variant="secondary" className="ml-1 px-1.5 py-0">
              {value[0].toFixed(1)} - {value[1].toFixed(1)}
            </Badge>
          )}
          <ChevronDown className="h-4 w-4 opacity-50" />
        </Button>
      </PopoverTrigger>

      <PopoverContent className="w-80" align="start">
        <div className="space-y-4">
          <div>
            <h4 className="font-semibold text-sm mb-3">Rating Range</h4>
            <div className="flex items-center gap-2 mb-4">
              <span className="text-sm text-muted-foreground">
                {localValue[0].toFixed(1)}
              </span>
              <div className="flex-1 h-2 bg-muted rounded-full relative">
                <div
                  className="absolute h-full bg-primary rounded-full"
                  style={{
                    left: `${(localValue[0] / 10) * 100}%`,
                    right: `${100 - (localValue[1] / 10) * 100}%`,
                  }}
                />
              </div>
              <span className="text-sm text-muted-foreground">
                {localValue[1].toFixed(1)}
              </span>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">
                  Minimum Rating
                </label>
                <input
                  type="range"
                  min="0"
                  max="10"
                  step="0.1"
                  value={localValue[0]}
                  onChange={(e) =>
                    setLocalValue([parseFloat(e.target.value), localValue[1]])
                  }
                  className="w-full"
                />
              </div>

              <div>
                <label className="text-xs text-muted-foreground mb-1 block">
                  Maximum Rating
                </label>
                <input
                  type="range"
                  min="0"
                  max="10"
                  step="0.1"
                  value={localValue[1]}
                  onChange={(e) =>
                    setLocalValue([localValue[0], parseFloat(e.target.value)])
                  }
                  className="w-full"
                />
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setLocalValue([0, 10]);
                onChange([0, 10]);
                setIsOpen(false);
              }}
              className="flex-1"
            >
              Reset
            </Button>
            <Button
              size="sm"
              onClick={handleApply}
              className="flex-1"
            >
              Apply
            </Button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function AdvancedFilters({
  options,
  filters,
  onFiltersChange,
  isLoading,
}: AdvancedFiltersProps) {
  const handleFilterRemove = (type: keyof FilterState, value: string | null) => {
    if (type === 'ratingRange') {
      onFiltersChange({ ...filters, ratingRange: [0, 10] });
    } else {
      const updated = filters[type].filter((v) => v !== value);
      onFiltersChange({ ...filters, [type]: updated });
    }
  };

  const handleReset = () => {
    onFiltersChange({
      countries: [],
      organizations: [],
      topics: [],
      keywords: [],
      ratingRange: [0, 10],
    });
  };

  return (
    <div className="space-y-4">
      {/* Filter Controls */}
      <div className="flex flex-wrap items-center gap-2">
        <MultiSelectFilter
          label="Countries"
          icon={Globe}
          options={options.countries}
          selected={filters.countries}
          onSelectionChange={(selected) =>
            onFiltersChange({ ...filters, countries: selected })
          }
        />

        <MultiSelectFilter
          label="Organizations"
          icon={Building2}
          options={options.organizations}
          selected={filters.organizations}
          onSelectionChange={(selected) =>
            onFiltersChange({ ...filters, organizations: selected })
          }
        />

        <MultiSelectFilter
          label="Topics"
          icon={Tag}
          options={options.topics}
          selected={filters.topics}
          onSelectionChange={(selected) =>
            onFiltersChange({ ...filters, topics: selected })
          }
        />

        <RatingRangeSlider
          value={filters.ratingRange}
          onChange={(value) =>
            onFiltersChange({ ...filters, ratingRange: value })
          }
        />
      </div>

      {/* Active Filter Chips */}
      <FilterChips
        filters={filters}
        onRemove={handleFilterRemove}
        onReset={handleReset}
      />
    </div>
  );
}

export default AdvancedFilters;
