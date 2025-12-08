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
  Search,
  ChevronLeft,
  ChevronRight,
  Settings,
  Filter,
} from 'lucide-react';
import { splitSemicolonValues, formatTruncatedList } from '@/shared/utils/utils';
import { Checkbox } from '@/shared/components/ui/checkbox';
import { Button } from '@/shared/components/ui/button';

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
  showSearch?: boolean; // New prop to control search bar visibility
  enableClientPagination?: boolean; // New prop to enable client-side pagination
  showTitle?: boolean; // New prop to control title visibility
  // External selection control
  externalSelectedIds?: Set<string>;
  onSelectionChange?: (ids: Set<string>) => void;
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
  <div className="w-full">
    <div className="h-7 bg-gray-100 rounded animate-pulse w-48 mb-6" />

    {/* Filters skeleton */}
    <div className="flex flex-wrap gap-4 mb-6">
      <div className="h-10 bg-gray-100 rounded animate-pulse w-64" />
      <div className="h-10 bg-gray-100 rounded animate-pulse w-40" />
      <div className="h-10 bg-gray-100 rounded animate-pulse w-32" />
    </div>

    {/* Table skeleton */}
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="h-20 bg-gray-50 rounded-lg animate-pulse" />
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
  isExpanded: boolean;
  onToggleExpand: () => void;
}

const PublicationRow = memo(({
  publication,
  columnVisibility,
  isSelected,
  onToggleSelect,
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

  // Calculate visible columns count for colSpan
  const visibleColumnsCount = useMemo(() => {
    let count = 3; // Checkbox, Title, Authors
    if (columnVisibility.affiliation) count++;
    if (columnVisibility.topic) count++;
    if (columnVisibility.rating) count++;
    if (columnVisibility.links) count++;
    return count;
  }, [columnVisibility]);

  return (
    <>
      <tr className={`group border-b border-gray-100 hover:bg-gray-50/80 transition-colors ${isExpanded ? 'bg-gray-50/50' : ''}`}>
        {/* Selection Checkbox */}
        <td className="py-3 px-4 w-12 align-top">
          <Checkbox
            checked={isSelected}
            onCheckedChange={onToggleSelect}
            className="cursor-pointer mt-1"
          />
        </td>

        {/* Title - Always visible, clickable to expand */}
        <td
          className="py-3 px-4 cursor-pointer align-top"
          onClick={onToggleExpand}
        >
          <div className="space-y-2">
            <div className="font-medium text-gray-900 text-[15px] leading-snug hover:text-blue-600 transition-colors">
              {publication.title}
            </div>
            {columnVisibility.keywords && keywords.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {keywords.slice(0, 4).map((keyword, i) => (
                  <span key={i} className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-gray-100 text-gray-600">
                    {keyword}
                  </span>
                ))}
                {keywords.length > 4 && (
                  <span className="text-[11px] text-gray-400 self-center">+{keywords.length - 4}</span>
                )}
              </div>
            )}
          </div>
        </td>

        {/* Authors - Always visible */}
        <td className="py-3 px-4 align-top">
          <div className="space-y-2">
            <div className="text-sm text-gray-700 leading-relaxed">
              {authorsDisplay.displayText}
              {authorsDisplay.hasMore && (
                <span className="text-gray-400 text-xs ml-1">+{authorsDisplay.remainingCount}</span>
              )}
            </div>
            {columnVisibility.countries && countries.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {countriesDisplay.displayItems.map((country, index) => (
                  <span key={index} className="inline-flex items-center px-1.5 py-0.5 text-[10px] bg-blue-50 text-blue-700 rounded border border-blue-100">
                    {country}
                  </span>
                ))}
              </div>
            )}
          </div>
        </td>

        {/* Affiliation - Conditional */}
        {columnVisibility.affiliation && (
          <td className="py-3 px-4 align-top">
            {affiliations.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {affiliationsDisplay.displayItems.map((affiliation, index) => (
                  <span key={index} className="inline-flex items-center px-2 py-0.5 text-[11px] bg-gray-50 text-gray-700 rounded border border-gray-100">
                    {affiliation}
                  </span>
                ))}
                {affiliationsDisplay.hasMore && (
                  <span className="text-xs text-gray-400 self-center">
                    +{affiliationsDisplay.remainingCount}
                  </span>
                )}
              </div>
            )}
          </td>
        )}

        {/* Topic - Conditional */}
        {columnVisibility.topic && (
          <td className="py-3 px-4 align-top">
            {publication.research_topic && (
              <span
                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-50 text-purple-700 max-w-full"
                title={publication.research_topic}
              >
                <span className="truncate block">
                  {publication.research_topic}
                </span>
              </span>
            )}
          </td>
        )}

        {/* Rating - Conditional */}
        {columnVisibility.rating && (
          <td className="py-3 px-4 align-top">
            {publication.rating && !isNaN(Number(publication.rating)) && (
              <div className="bg-amber-50 px-2 py-1 rounded-md w-fit">
                <span className="text-sm font-bold text-amber-700">
                  {Number(publication.rating).toFixed(1)}
                </span>
              </div>
            )}
          </td>
        )}

        {/* Links - Conditional */}
        {columnVisibility.links && (
          <td className="py-3 px-4 align-top">
            <div className="flex items-center gap-1">
              {publication.pdf_url && (
                <a
                  href={publication.pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-all"
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
                  className="p-1.5 text-gray-400 hover:text-gray-900 hover:bg-gray-100 rounded transition-all"
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
                  className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-all"
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
        <tr className="bg-gray-50/50 border-b border-gray-100">
          <td colSpan={visibleColumnsCount} className="py-0">
            <div
              className="animate-in slide-in-from-top-2 duration-200 overflow-hidden"
              style={{
                maxHeight: isExpanded ? '500px' : '0',
                transition: 'max-height 0.3s ease-in-out',
              }}
            >
              <div className="px-12 py-4 flex gap-6">
                <div className="w-1 bg-blue-500 rounded-full flex-shrink-0 self-stretch opacity-20" />

                <div className="space-y-2 flex-1 max-w-3xl">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500 flex items-center gap-2">
                    Abstract
                  </h4>
                  {publication.abstract ? (
                    <p className="text-sm text-gray-700 leading-6 text-justify">
                      {publication.abstract}
                    </p>
                  ) : (
                    <p className="text-sm text-gray-400 italic">
                      No abstract available
                    </p>
                  )}
                </div>
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

  expandedIds: Set<string>;
  onToggleExpand: (id: string) => void;
}

const TableBody = memo(({
  data,
  columnVisibility,
  selectedIds,
  onToggleSelect,

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

const PublicationsTable = ({
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
  showSearch = true, // Default to true
  enableClientPagination = false, // Default to false
  showTitle = true, // Default to true
  externalSelectedIds,
  onSelectionChange,
}: PublicationsTableProps) => {
  const [showColumnSettings, setShowColumnSettings] = useState(false);
  const [showAffiliationFilter, setShowAffiliationFilter] = useState(false);
  const [internalSelectedIds, setInternalSelectedIds] = useState<Set<string>>(new Set());
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // Use external or internal state
  const selectedIds = externalSelectedIds || internalSelectedIds;
  const handleSelectionChange = (newIds: Set<string>) => {
    if (onSelectionChange) {
      onSelectionChange(newIds);
    } else {
      setInternalSelectedIds(newIds);
    }
  };

  // Column visibility state
  const [columnVisibility, setColumnVisibility] = useState<ColumnVisibility>({
    title: true,
    authors: true,
    affiliation: true,
    topic: true,
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

  // Determine which data to display (client-side pagination vs server-side)
  const displayData = useMemo(() => {
    let processedData = data;

    // Apply client-side pagination if enabled
    if (enableClientPagination) {
      const startIndex = (currentPage - 1) * 20;
      return processedData.slice(startIndex, startIndex + 20);
    }

    return processedData;
  }, [data, enableClientPagination, currentPage]);

  // Selection handlers
  const toggleSelectAll = () => {
    // Select all items on the CURRENT PAGE only
    const currentPageIds = displayData.map((p) => String(p.id));
    const allCurrentPageSelected = currentPageIds.every(id => selectedIds.has(id));

    const next = new Set(selectedIds);

    if (allCurrentPageSelected) {
      // Deselect all items on current page
      currentPageIds.forEach(id => next.delete(id));
    } else {
      // Select all items on current page
      currentPageIds.forEach(id => next.add(id));
    }

    handleSelectionChange(next);
  };

  const toggleSelect = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    handleSelectionChange(next);
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

  // Get selected publications for export - USE FULL DATA
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

  // Check selection status against CURRENT PAGE only
  const currentPageIds = displayData.map((p) => String(p.id));
  const allCurrentPageSelected = currentPageIds.length > 0 && currentPageIds.every(id => selectedIds.has(id));
  const someCurrentPageSelected = currentPageIds.some(id => selectedIds.has(id)) && !allCurrentPageSelected;



  return (
    <>
      <div className="w-full">
        {/* Header Section - Cleaner, no background */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          {showTitle ? (
            <div>
              <h2 className="text-xl font-bold text-gray-900 tracking-tight">
                Publications
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                {pagination.count.toLocaleString()} results found
                {isFiltered && ' (filtered)'}
              </p>
            </div>
          ) : (
            <div /> // Spacer to keep flex layout working if needed, or just empty
          )}
        </div>

        {/* Controls - Only show if showSearch is true */}
        {showSearch && (
          <div className="flex flex-wrap gap-3 mb-6 p-1">
            <div className="relative flex-1 min-w-[240px]">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
              <input
                type="text"
                placeholder="Search titles, authors, keywords..."
                value={searchTerm}
                onChange={(e) => onSearchChange(e.target.value)}
                className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-black/5 focus:border-black transition-all text-sm"
              />
            </div>

            <select
              value={`${sortField}-${sortDirection}`}
              onChange={(e) => {
                const [field, direction] = e.target.value.split('-') as [SortField, SortDirection];
                onSortChange(field, direction);
              }}
              className="px-3 py-2 border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-black/5 focus:border-black transition-all text-sm cursor-pointer min-w-[180px]"
            >
              <option value="rating-desc">Highest Rated</option>
              <option value="rating-asc">Lowest Rated</option>
              <option value="title-asc">Title (A-Z)</option>
              <option value="title-desc">Title (Z-A)</option>
            </select>

            <div className="relative" ref={columnSettingsRef}>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowColumnSettings(!showColumnSettings)}
                className="h-[38px] border-gray-200"
              >
                <Settings size={14} className="mr-2" />
                View
              </Button>

              {showColumnSettings && (
                <div className="absolute right-0 top-full mt-2 w-56 bg-white border border-gray-100 rounded-xl shadow-xl z-20 p-2 animate-in fade-in slide-in-from-top-2 duration-200">
                  <h4 className="font-semibold text-xs text-gray-500 uppercase tracking-wider px-2 py-2 mb-1">Visible Columns</h4>
                  <div className="space-y-0.5">
                    {Object.entries(columnVisibility).map(([key, visible]) => {
                      const isRequired = key === 'title' || key === 'authors';
                      const label = key.charAt(0).toUpperCase() + key.slice(1);

                      return (
                        <label
                          key={key}
                          className="flex items-center gap-2 py-1.5 px-2 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                        >
                          <Checkbox
                            checked={visible}
                            onCheckedChange={() => toggleColumn(key as keyof ColumnVisibility)}
                            disabled={isRequired}
                            className="w-4 h-4"
                          />
                          <span className={`text-sm ${isRequired ? 'text-gray-400' : 'text-gray-700'}`}>
                            {label}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Table */}
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full table-fixed min-w-[1000px]">
              <thead className="bg-gray-50/80 border-b border-gray-200">
                <tr>
                  <th className="py-3 px-4 w-12 align-middle">
                    <Checkbox
                      checked={allCurrentPageSelected || someCurrentPageSelected}
                      onCheckedChange={toggleSelectAll}
                      className="mt-0.5"
                    />
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-900 text-xs uppercase tracking-wider">Title</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-900 text-xs uppercase tracking-wider w-[18%]">Authors</th>
                  {columnVisibility.affiliation && (
                    <th className="text-left py-3 px-4 font-semibold text-gray-900 text-xs uppercase tracking-wider w-[14%]">
                      <div className="flex items-center gap-1.5">
                        <span>Affiliation</span>
                        <div className="relative" ref={affiliationFilterRef}>
                          <button
                            onClick={() => setShowAffiliationFilter(!showAffiliationFilter)}
                            className={`p-1 rounded hover:bg-gray-200 transition-colors ${selectedAffiliations.length > 0 ? 'text-blue-600' : 'text-gray-400'
                              }`}
                          >
                            <Filter className="h-3 w-3" />
                          </button>

                          {showAffiliationFilter && onAffiliationFilterChange && (
                            <div className="absolute left-0 top-full mt-2 w-72 bg-white border border-gray-100 rounded-xl shadow-xl z-20 max-h-[400px] flex flex-col animate-in fade-in slide-in-from-top-2 duration-200">
                              <div className="p-3 border-b border-gray-100 bg-gray-50/50 rounded-t-xl">
                                <div className="flex gap-2">
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => onAffiliationFilterChange(uniqueAffiliations)}
                                    className="flex-1 h-8 text-xs bg-white"
                                  >
                                    Select All
                                  </Button>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => onAffiliationFilterChange([])}
                                    className="flex-1 h-8 text-xs bg-white"
                                  >
                                    Clear
                                  </Button>
                                </div>
                              </div>

                              <div className="overflow-y-auto p-2 space-y-0.5 flex-1">
                                {uniqueAffiliations.map((affiliation) => (
                                  <label
                                    key={affiliation}
                                    className="flex items-center gap-2 py-1.5 px-2 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
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
                                      className="w-3.5 h-3.5"
                                    />
                                    <span className="text-xs text-gray-700 flex-1 truncate">{affiliation}</span>
                                  </label>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </th>
                  )}
                  {columnVisibility.topic && (
                    <th className="text-left py-3 px-4 font-semibold text-gray-900 text-xs uppercase tracking-wider w-[10%]">Topic</th>
                  )}
                  {columnVisibility.rating && (
                    <th className="text-left py-3 px-4 font-semibold text-gray-900 text-xs uppercase tracking-wider w-[8%]">Rating</th>
                  )}
                  {columnVisibility.links && (
                    <th className="text-left py-3 px-4 font-semibold text-gray-900 text-xs uppercase tracking-wider w-[8%]">Links</th>
                  )}
                </tr>
              </thead>
              <TableBody
                data={displayData}
                columnVisibility={columnVisibility}
                selectedIds={selectedIds}
                onToggleSelect={toggleSelect}
                expandedIds={expandedIds}
                onToggleExpand={toggleExpand}
              />
            </table>
          </div>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-6 px-1">
            <div className="text-sm text-gray-500">
              Page {currentPage} of {totalPages}
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onPageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="h-9 w-9 p-0 rounded-lg border-gray-200"
              >
                <ChevronLeft size={16} />
              </Button>

              <div className="flex gap-1.5">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  // Logic to center the current page
                  let startPage = Math.max(1, currentPage - 2);
                  if (startPage + 4 > totalPages) {
                    startPage = Math.max(1, totalPages - 4);
                  }
                  const page = startPage + i;

                  if (page > totalPages) return null;

                  return (
                    <Button
                      key={page}
                      variant={currentPage === page ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => onPageChange(page)}
                      className={`h-9 min-w-[2.25rem] rounded-lg text-sm font-medium transition-all ${currentPage === page
                        ? 'bg-black text-white hover:bg-gray-800 border-transparent shadow-md'
                        : 'border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                        }`}
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
                className="h-9 w-9 p-0 rounded-lg border-gray-200"
              >
                <ChevronRight size={16} />
              </Button>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default PublicationsTable;
