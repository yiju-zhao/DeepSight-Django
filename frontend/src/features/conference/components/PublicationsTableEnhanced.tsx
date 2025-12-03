/**
 * Enhanced Publications Table Component
 *
 * Modern redesign with:
 * - Favorite/bookmark functionality
 * - Batch selection and export
 * - Detail view modal trigger
 * - Improved styling and animations
 * - Better responsive design
 */

import { useState, useMemo, memo, useEffect, useRef } from 'react';
import { PublicationTableItem, PaginationInfo } from '../types';
import {
  ExternalLink,
  Github,
  FileText,
  Star,
  Search,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Settings,
  Filter,
} from 'lucide-react';
import { splitSemicolonValues, formatTruncatedList } from '@/shared/utils/utils';
import { Checkbox } from '@/shared/components/ui/checkbox';
import { Button } from '@/shared/components/ui/button';
import ExportButton from './ExportButton';
import { ImportToNotebookWizard } from './ImportToNotebookWizard';
import { useFavorites } from '../hooks/useFavorites';
import type { ImportResponse } from '../types';

interface PublicationsTableProps {
  data: PublicationTableItem[];
  pagination: PaginationInfo;
  currentPage: number;
  onPageChange: (page: number) => void;
  searchTerm: string;
  onSearchChange: (search: string) => void;
  selectedAffiliations?: string[];
  onAffiliationFilterChange?: (affiliations: string[]) => void;
  sortField: SortField;
  sortDirection: SortDirection;
  onSortChange: (field: SortField, direction: SortDirection) => void;
  isFiltered: boolean;
  isLoading?: boolean;
}

interface ColumnVisibility {
  title: boolean;
  authors: boolean;
  affiliation: boolean;
  topic: boolean;
  rating: boolean;
  links: boolean;
  keywords: boolean;
  countries: boolean;
}

type SortField = 'rating' | 'title';
type SortDirection = 'asc' | 'desc';

// ============================================================================
// LOADING SKELETON
// ============================================================================

const LoadingSkeleton = () => (
  <div className="bg-white rounded-lg shadow-[rgba(0,0,0,0.08)_0px_8px_12px] p-6">
    <div className="h-7 bg-[#F5F5F5] rounded animate-pulse w-48 mb-6" />

    {/* Filters skeleton */}
    <div className="flex flex-wrap gap-4 mb-6">
      <div className="h-10 bg-[#F5F5F5] rounded animate-pulse w-64" />
      <div className="h-10 bg-[#F5F5F5] rounded animate-pulse w-40" />
      <div className="h-10 bg-[#F5F5F5] rounded animate-pulse w-32" />
    </div>

    {/* Table skeleton */}
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="h-20 bg-[#F5F5F5] rounded-lg animate-pulse" />
      ))}
    </div>
  </div>
);

// ============================================================================
// PUBLICATION ROW
// ============================================================================

interface PublicationRowProps {
  publication: PublicationTableItem;
  columnVisibility: ColumnVisibility;
  isSelected: boolean;
  onToggleSelect: () => void;
  isFavorite: boolean;
  onToggleFavorite: () => void;
  isExpanded: boolean;
  onToggleExpand: () => void;
}

const PublicationRow = memo(({
  publication,
  columnVisibility,
  isSelected,
  onToggleSelect,
  isFavorite,
  onToggleFavorite,
  isExpanded,
  onToggleExpand,
}: PublicationRowProps) => {
  const keywords = useMemo(() => splitSemicolonValues(publication.keywords), [publication.keywords]);
  const authors = useMemo(() => splitSemicolonValues(publication.authors), [publication.authors]);
  const countries = useMemo(() => splitSemicolonValues(publication.aff_country_unique), [publication.aff_country_unique]);
  const affiliations = useMemo(() => splitSemicolonValues(publication.aff_unique), [publication.aff_unique]);

  const keywordsDisplay = useMemo(() => formatTruncatedList(keywords, 3), [keywords]);
  const authorsDisplay = useMemo(() => formatTruncatedList(authors, 3), [authors]);
  const countriesDisplay = useMemo(() => formatTruncatedList(countries, 3), [countries]);
  const affiliationsDisplay = useMemo(() => formatTruncatedList(affiliations, 2), [affiliations]);

  return (
    <>
      <tr className="group border-b border-[#E3E3E3] hover:bg-gray-50/50 transition-colors">
        {/* Selection Checkbox */}
        <td className="py-4 px-4 w-12">
          <Checkbox
            checked={isSelected}
            onCheckedChange={onToggleSelect}
            className="cursor-pointer"
          />
        </td>

        {/* Favorite Icon */}
        <td className="py-4 px-2 w-12">
          <button
            onClick={onToggleFavorite}
            className={`p-1.5 rounded-md transition-all duration-200 ${isFavorite
                ? 'text-amber-500 hover:text-amber-600 hover:bg-amber-50'
                : 'text-[#666666] hover:text-amber-500 hover:bg-amber-50'
              }`}
            title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
          >
            {isFavorite ? (
              <Star className="h-4 w-4 fill-current" />
            ) : (
              <Star className="h-4 w-4" />
            )}
          </button>
        </td>

        {/* Title - Always visible with chevron */}
        <td className="py-4 px-4">
          <div
            className="flex items-start gap-2 cursor-pointer group/title"
            onClick={onToggleExpand}
          >
            <ChevronDown
              className={`h-4 w-4 text-gray-600 transition-transform duration-200 flex-shrink-0 mt-0.5 ${isExpanded ? 'rotate-180' : ''
                }`}
            />
            <div className="space-y-1.5 flex-1">
              <div className="font-medium text-foreground text-sm group-hover/title:text-blue-600 transition-colors">
                {publication.title}
              </div>
              {columnVisibility.keywords && keywords.length > 0 && (
                <div className="text-xs text-muted-foreground line-clamp-2">
                  {keywordsDisplay.displayText}
                </div>
              )}
            </div>
          </div>
        </td>

        {/* Authors - Always visible */}
        <td className="py-4 px-4">
          <div className="space-y-2">
            <div className="text-sm text-foreground">
              {authorsDisplay.displayText}
              {authorsDisplay.hasMore && (
                <span className="text-muted-foreground"> +{authorsDisplay.remainingCount} more</span>
              )}
            </div>
            {columnVisibility.countries && countries.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {countriesDisplay.displayItems.map((country, index) => (
                  <span key={index} className="inline-flex items-center px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded-md font-medium">
                    {country}
                  </span>
                ))}
                {countriesDisplay.hasMore && (
                  <span className="inline-flex items-center px-2 py-0.5 text-xs bg-muted text-muted-foreground rounded-md font-medium">
                    +{countriesDisplay.remainingCount}
                  </span>
                )}
              </div>
            )}
          </div>
        </td>

        {/* Affiliation - Conditional */}
        {columnVisibility.affiliation && (
          <td className="py-4 px-4">
            {affiliations.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {affiliationsDisplay.displayItems.map((affiliation, index) => (
                  <span key={index} className="inline-flex items-center px-2 py-0.5 text-xs bg-green-100 text-green-800 rounded-md font-medium">
                    {affiliation}
                  </span>
                ))}
                {affiliationsDisplay.hasMore && (
                  <span className="inline-flex items-center px-2 py-0.5 text-xs bg-muted text-muted-foreground rounded-md font-medium">
                    +{affiliationsDisplay.remainingCount}
                  </span>
                )}
              </div>
            )}
          </td>
        )}

        {/* Topic - Conditional */}
        {columnVisibility.topic && (
          <td className="py-4 px-4">
            <span className="text-sm text-foreground">
              {publication.research_topic}
            </span>
          </td>
        )}

        {/* Rating - Conditional */}
        {columnVisibility.rating && (
          <td className="py-4 px-4">
            {publication.rating && !isNaN(Number(publication.rating)) && (
              <div className="flex items-center gap-1.5">
                <Star className="w-4 h-4 text-amber-400 fill-current" />
                <span className="text-sm font-semibold text-foreground">
                  {Number(publication.rating).toFixed(1)}
                </span>
              </div>
            )}
          </td>
        )}

        {/* Links - Conditional */}
        {columnVisibility.links && (
          <td className="py-4 px-4">
            <div className="flex items-center gap-2">
              {publication.pdf_url && (
                <a
                  href={publication.pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1.5 text-red-600 hover:text-red-700 hover:bg-red-50 rounded-md transition-all"
                  title="View PDF"
                >
                  <FileText className="h-4 w-4" />
                </a>
              )}

              {publication.github && (
                <a
                  href={publication.github}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1.5 text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-all"
                  title="View GitHub"
                >
                  <Github className="h-4 w-4" />
                </a>
              )}

              {publication.site && (
                <a
                  href={publication.site}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1.5 text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-md transition-all"
                  title="View Project Site"
                >
                  <ExternalLink className="h-4 w-4" />
                </a>
              )}
            </div>
          </td>
        )}
      </tr>

      {/* Expanded Row - Abstract */}
      {isExpanded && (
        <tr className="bg-gray-50/80 border-b border-[#E3E3E3]">
          <td colSpan={100} className="py-0">
            <div
              className="px-6 py-4 animate-in slide-in-from-top-2 duration-200"
              style={{
                maxHeight: isExpanded ? '500px' : '0',
                overflow: 'hidden',
                transition: 'max-height 0.3s ease-in-out',
              }}
            >
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-gray-700">Abstract</h4>
                {publication.abstract ? (
                  <p className="text-sm text-gray-600 leading-relaxed">
                    {publication.abstract}
                  </p>
                ) : (
                  <p className="text-sm text-gray-400 italic">
                    No abstract available
                  </p>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
});

PublicationRow.displayName = 'PublicationRow';

// ============================================================================
// TABLE BODY
// ============================================================================

interface TableBodyProps {
  data: PublicationTableItem[];
  columnVisibility: ColumnVisibility;
  selectedIds: Set<string>;
  onToggleSelect: (id: string) => void;
  favorites: Set<string>;
  onToggleFavorite: (id: string) => void;
  expandedIds: Set<string>;
  onToggleExpand: (id: string) => void;
}

const TableBody = memo(({
  data,
  columnVisibility,
  selectedIds,
  onToggleSelect,
  favorites,
  onToggleFavorite,
  expandedIds,
  onToggleExpand,
}: TableBodyProps) => (
  <tbody>
    {data.map((publication) => (
      <PublicationRow
        key={publication.id}
        publication={publication}
        columnVisibility={columnVisibility}
        isSelected={selectedIds.has(String(publication.id))}
        onToggleSelect={() => onToggleSelect(String(publication.id))}
        isFavorite={favorites.has(String(publication.id))}
        onToggleFavorite={() => onToggleFavorite(String(publication.id))}
        isExpanded={expandedIds.has(String(publication.id))}
        onToggleExpand={() => onToggleExpand(String(publication.id))}
      />
    ))}
  </tbody>
));

TableBody.displayName = 'TableBody';

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const PublicationsTableComponent = ({
  data,
  pagination,
  currentPage,
  onPageChange,
  searchTerm,
  onSearchChange,
  selectedAffiliations = [],
  onAffiliationFilterChange,
  sortField,
  sortDirection,
  onSortChange,
  isFiltered,
  isLoading,
}: PublicationsTableProps) => {
  const [showColumnSettings, setShowColumnSettings] = useState(false);
  const [showAffiliationFilter, setShowAffiliationFilter] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showImportWizard, setShowImportWizard] = useState(false);
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const { favorites, toggleFavorite } = useFavorites();

  // Column visibility state
  const [columnVisibility, setColumnVisibility] = useState<ColumnVisibility>({
    title: true,
    authors: true,
    affiliation: true,
    topic: false,
    rating: true,
    links: true,
    keywords: true,
    countries: false,
  });

  const toggleColumn = (column: keyof ColumnVisibility) => {
    if (column === 'title' || column === 'authors') return;
    setColumnVisibility((prev) => ({
      ...prev,
      [column]: !prev[column],
    }));
  };

  // Filter data based on favorites
  const filteredData = useMemo(() => {
    if (!showFavoritesOnly) return data;
    return data.filter(pub => favorites.has(String(pub.id)));
  }, [data, showFavoritesOnly, favorites]);

  // Selection handlers
  const toggleSelectAll = () => {
    if (selectedIds.size === filteredData.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredData.map((p) => String(p.id))));
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Get selected publications for export
  const selectedPublications = useMemo(() => {
    return data.filter((p) => selectedIds.has(String(p.id)));
  }, [data, selectedIds]);

  // Ref for column settings dropdown and affiliation filter dropdown
  const columnSettingsRef = useRef<HTMLDivElement>(null);
  const affiliationFilterRef = useRef<HTMLDivElement>(null);

  // Extract unique affiliations from current data for filter options
  const uniqueAffiliations = useMemo(() => {
    const affiliationsSet = new Set<string>();
    data.forEach(pub => {
      if (pub.aff_unique) {
        const affiliations = splitSemicolonValues(pub.aff_unique);
        affiliations.forEach(aff => {
          if (aff.trim()) {
            affiliationsSet.add(aff.trim());
          }
        });
      }
    });
    return Array.from(affiliationsSet).sort();
  }, [data]);

  // Close column settings when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (columnSettingsRef.current && !columnSettingsRef.current.contains(event.target as Node)) {
        setShowColumnSettings(false);
      }
      if (affiliationFilterRef.current && !affiliationFilterRef.current.contains(event.target as Node)) {
        setShowAffiliationFilter(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  const totalPages = Math.ceil(pagination.count / 20);
  const allSelected = filteredData.length > 0 && selectedIds.size === filteredData.length;
  const someSelected = selectedIds.size > 0 && selectedIds.size < filteredData.length;

  const handleImportComplete = (response: ImportResponse) => {
    // Clear selection after successful import
    if (response.success) {
      setSelectedIds(new Set());
    }
  };

  const handleOpenImportWizard = () => {
    if (selectedIds.size === 0) {
      alert('Please select publications to import');
      return;
    }
    setShowImportWizard(true);
  };

  return (
    <>
      <div className="bg-white rounded-lg shadow-[rgba(0,0,0,0.08)_0px_8px_12px] overflow-hidden">
        {/* Header Section - HUAWEI Style */}
        <div className="border-b border-[#E3E3E3] bg-[#F5F5F5] px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-[#1E1E1E]">
                Publications
              </h2>
              <p className="text-sm text-[#666666] mt-1">
                {pagination.count.toLocaleString()} total publications
                {isFiltered && ' (filtered)'}
              </p>
            </div>

            <div className="flex items-center gap-3">
              {selectedIds.size > 0 && (
                <span className="text-sm font-medium text-[#666666]">
                  {selectedIds.size} selected
                </span>
              )}

              <Button
                onClick={handleOpenImportWizard}
                variant="outline"
                size="sm"
                disabled={selectedIds.size === 0}
                className="flex items-center gap-2"
              >
                <FileText size={16} />
                Import to Notebook ({selectedIds.size})
              </Button>

              <ExportButton
                publications={data}
                selectedPublications={selectedPublications}
                variant="outline"
                size="sm"
              />
            </div>
          </div>
        </div>

        <div className="p-6">
          {/* Controls - HUAWEI Style */}
          <div className="flex flex-wrap gap-4 mb-6">
            <div className="relative flex-1 min-w-64">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[#666666]" size={18} />
              <input
                type="text"
                placeholder="Search titles, authors, keywords..."
                value={searchTerm}
                onChange={(e) => onSearchChange(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 border border-[#E3E3E3] rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-black/10 focus:border-black transition-all duration-300 text-sm text-[#1E1E1E] placeholder-[#666666]"
              />
            </div>

            <select
              value={`${sortField}-${sortDirection}`}
              onChange={(e) => {
                const [field, direction] = e.target.value.split('-') as [SortField, SortDirection];
                onSortChange(field, direction);
              }}
              className="px-4 py-2.5 border border-[#E3E3E3] rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-black/10 focus:border-black transition-all duration-300 text-sm text-[#1E1E1E] cursor-pointer"
            >
              <option value="rating-desc">Sort by Rating (High to Low)</option>
              <option value="rating-asc">Sort by Rating (Low to High)</option>
              <option value="title-asc">Sort by Title (A to Z)</option>
              <option value="title-desc">Sort by Title (Z to A)</option>
            </select>

            <div className="relative" ref={columnSettingsRef}>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowColumnSettings(!showColumnSettings)}
              >
                <Settings size={16} className="mr-2" />
                Columns
              </Button>

              {showColumnSettings && (
                <div className="absolute right-0 top-full mt-2 w-64 bg-popover border border-border rounded-lg shadow-lg z-10">
                  <div className="p-4">
                    <h4 className="font-semibold text-sm text-foreground mb-3">Show/Hide Columns</h4>
                    <div className="space-y-2">
                      {Object.entries(columnVisibility).map(([key, visible]) => {
                        const isRequired = key === 'title' || key === 'authors';
                        const label = key.charAt(0).toUpperCase() + key.slice(1);

                        return (
                          <label
                            key={key}
                            className="flex items-center gap-2 py-1 px-2 rounded-md hover:bg-accent cursor-pointer"
                          >
                            <Checkbox
                              checked={visible}
                              onCheckedChange={() => toggleColumn(key as keyof ColumnVisibility)}
                              disabled={isRequired}
                            />
                            <span className={`text-sm ${isRequired ? 'text-muted-foreground' : 'text-foreground'}`}>
                              {label} {isRequired && '(Required)'}
                            </span>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full" style={{ tableLayout: 'fixed' }}>
              <thead className="bg-muted/50">
                <tr className="border-b border-border">
                  <th className="py-3 px-4 w-12">
                    <Checkbox
                      checked={allSelected || someSelected}
                      onCheckedChange={toggleSelectAll}
                    />
                  </th>
                  <th className="py-3 px-2 w-12">
                    <button
                      onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
                      className={`p-1.5 rounded-md transition-all duration-200 ${showFavoritesOnly
                        ? 'text-amber-500 hover:text-amber-600 hover:bg-amber-50'
                        : 'text-muted-foreground hover:text-amber-500 hover:bg-amber-50'
                        }`}
                      title={showFavoritesOnly ? 'Show all publications' : 'Show favorites only'}
                    >
                      <Star className={`h-4 w-4 ${showFavoritesOnly ? 'fill-current' : ''}`} />
                    </button>
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-foreground text-sm">Title</th>
                  <th className="text-left py-3 px-4 font-semibold text-foreground text-sm">Authors</th>
                  {columnVisibility.affiliation && (
                    <th className="text-left py-3 px-4 font-semibold text-foreground text-sm">
                      <div className="flex items-center gap-2">
                        <span>Affiliation</span>
                        <div className="relative" ref={affiliationFilterRef}>
                          <button
                            onClick={() => setShowAffiliationFilter(!showAffiliationFilter)}
                            className={`p-1 rounded hover:bg-accent transition-colors ${selectedAffiliations.length > 0 ? 'text-primary' : 'text-muted-foreground'
                              }`}
                            title="Filter by affiliation"
                          >
                            <Filter className="h-4 w-4" />
                          </button>

                          {showAffiliationFilter && onAffiliationFilterChange && (
                            <div className="absolute left-0 top-full mt-2 w-80 bg-popover border border-border rounded-lg shadow-lg z-20 max-h-96 overflow-hidden flex flex-col">
                              <div className="p-3 border-b border-border">
                                <h4 className="font-semibold text-sm text-foreground mb-2">Filter by Affiliation</h4>
                                <div className="flex gap-2">
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => onAffiliationFilterChange(uniqueAffiliations)}
                                    className="flex-1"
                                  >
                                    Select All
                                  </Button>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => onAffiliationFilterChange([])}
                                    className="flex-1"
                                  >
                                    Clear All
                                  </Button>
                                </div>
                              </div>

                              <div className="overflow-y-auto max-h-64 p-2">
                                {uniqueAffiliations.map((affiliation) => (
                                  <label
                                    key={affiliation}
                                    className="flex items-center gap-2 py-2 px-2 rounded-md hover:bg-accent cursor-pointer"
                                  >
                                    <Checkbox
                                      checked={selectedAffiliations.includes(affiliation)}
                                      onCheckedChange={(checked) => {
                                        if (checked) {
                                          onAffiliationFilterChange([...selectedAffiliations, affiliation]);
                                        } else {
                                          onAffiliationFilterChange(selectedAffiliations.filter(a => a !== affiliation));
                                        }
                                      }}
                                    />
                                    <span className="text-sm text-foreground flex-1">{affiliation}</span>
                                  </label>
                                ))}
                              </div>

                              <div className="p-3 border-t border-border bg-muted/30">
                                <div className="text-xs text-muted-foreground">
                                  {selectedAffiliations.length} of {uniqueAffiliations.length} selected
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </th>
                  )}
                  {columnVisibility.topic && (
                    <th className="text-left py-3 px-4 font-semibold text-foreground text-sm">Topic</th>
                  )}
                  {columnVisibility.rating && (
                    <th className="text-left py-3 px-4 font-semibold text-foreground text-sm">Rating</th>
                  )}
                  {columnVisibility.links && (
                    <th className="text-left py-3 px-4 font-semibold text-foreground text-sm">Links</th>
                  )}
                </tr>
              </thead>
              <TableBody
                data={filteredData}
                columnVisibility={columnVisibility}
                selectedIds={selectedIds}
                onToggleSelect={toggleSelect}
                favorites={favorites}
                onToggleFavorite={toggleFavorite}
                expandedIds={expandedIds}
                onToggleExpand={toggleExpand}
              />
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onPageChange(currentPage - 1)}
                disabled={currentPage === 1}
              >
                <ChevronLeft size={16} className="mr-1" />
                Previous
              </Button>

              <div className="flex gap-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  const page = Math.max(1, Math.min(totalPages - 4, currentPage - 2)) + i;
                  if (page > totalPages) return null;

                  return (
                    <Button
                      key={page}
                      variant={currentPage === page ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => onPageChange(page)}
                      className="min-w-[2.5rem]"
                    >
                      {page}
                    </Button>
                  );
                })}
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={() => onPageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                Next
                <ChevronRight size={16} className="ml-1" />
              </Button>
            </div>
          )}

          {/* Results Info - HUAWEI Style */}
          <div className="text-sm text-[#666666] text-center mt-6">
            Showing {filteredData.length} of {pagination.count.toLocaleString()} publications
            {showFavoritesOnly && ' (favorites only)'}
          </div>
        </div>

        {/* Import To Notebook Wizard */}
        <ImportToNotebookWizard
          isOpen={showImportWizard}
          onClose={() => setShowImportWizard(false)}
          selectedPublicationIds={Array.from(selectedIds)}
          onImportComplete={handleImportComplete}
        />
      </div>
    </>
  );
};

PublicationsTableComponent.displayName = 'PublicationsTableEnhanced';

export const PublicationsTableEnhanced = memo(PublicationsTableComponent);
export default PublicationsTableEnhanced;
