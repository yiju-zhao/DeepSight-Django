import { useState, useMemo, memo, useEffect, useRef } from 'react';
import { PublicationTableItem, PaginationInfo } from '../types';
import {
  ExternalLink,
  Github,
  FileText,
  Star,
  StarOff,
  Search,
  ChevronLeft,
  ChevronRight,
  Settings,
  Eye,
} from 'lucide-react';
import { splitSemicolonValues, formatTruncatedList } from '@/shared/utils/utils';
import { Card, CardHeader, CardContent } from '@/shared/components/ui/card';
import { Checkbox } from '@/shared/components/ui/checkbox';
import ExportButton from './ExportButton';
import { useFavorites } from '../hooks/useFavorites';

interface PublicationsTableProps {
  data: PublicationTableItem[];
  pagination: PaginationInfo;
  currentPage: number;
  onPageChange: (page: number) => void;
  searchTerm: string;
  onSearchChange: (search: string) => void;
  sortField: SortField;
  sortDirection: SortDirection;
  onSortChange: (field: SortField, direction: SortDirection) => void;
  isFiltered: boolean; // Whether results are currently filtered
  isLoading?: boolean;
}

interface ColumnVisibility {
  title: boolean;
  authors: boolean;
  topic: boolean;
  rating: boolean;
  links: boolean;
  keywords: boolean;
  countries: boolean;
}

type SortField = 'rating' | 'title';
type SortDirection = 'asc' | 'desc';

const LoadingSkeleton = () => (
  <div className="bg-white rounded-lg shadow-sm border">
    <div className="p-6">
      <div className="h-6 bg-gray-200 rounded animate-pulse w-48 mb-4" />

      {/* Filters skeleton */}
      <div className="flex flex-wrap gap-4 mb-6">
        <div className="h-10 bg-gray-200 rounded animate-pulse w-64" />
        <div className="h-10 bg-gray-200 rounded animate-pulse w-40" />
        <div className="h-10 bg-gray-200 rounded animate-pulse w-32" />
      </div>

      {/* Table skeleton */}
      <div className="space-y-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-16 bg-gray-200 rounded animate-pulse" />
        ))}
      </div>
    </div>
  </div>
);

const PublicationRow = memo(({ publication, columnVisibility }: { publication: PublicationTableItem; columnVisibility: ColumnVisibility }) => {
  const keywords = useMemo(() => splitSemicolonValues(publication.keywords), [publication.keywords]);
  const authors = useMemo(() => splitSemicolonValues(publication.authors), [publication.authors]);
  const countries = useMemo(() => splitSemicolonValues(publication.aff_country_unique), [publication.aff_country_unique]);

  const keywordsDisplay = useMemo(() => formatTruncatedList(keywords, 3), [keywords]);
  const authorsDisplay = useMemo(() => formatTruncatedList(authors, 3), [authors]);
  const countriesDisplay = useMemo(() => formatTruncatedList(countries, 3), [countries]);

  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
      {/* Title - Always visible */}
      <td className="py-4 px-4">
        <div className="space-y-1">
          <div className="font-medium text-gray-900 text-sm">
            {publication.title}
          </div>
          {columnVisibility.keywords && (
            <div className="text-xs text-gray-600 line-clamp-2">
              {keywordsDisplay.displayText}
            </div>
          )}
        </div>
      </td>

      {/* Authors - Always visible */}
      <td className="py-4 px-4">
        <div className="space-y-2">
          <div className="text-sm text-gray-900">
            {authorsDisplay.displayText}
            {authorsDisplay.hasMore && (
              <span className="text-gray-500"> +{authorsDisplay.remainingCount} more</span>
            )}
          </div>
          {columnVisibility.countries && publication.aff_country_unique && (
            <div className="flex flex-wrap gap-1">
              {countriesDisplay.displayItems.map((country, index) => (
                <span key={index} className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                  {country}
                </span>
              ))}
              {countriesDisplay.hasMore && (
                <span className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">
                  +{countriesDisplay.remainingCount}
                </span>
              )}
            </div>
          )}
        </div>
      </td>

      {/* Topic - Conditional */}
      {columnVisibility.topic && (
        <td className="py-4 px-4">
          <span className="text-sm text-gray-900">
            {publication.research_topic}
          </span>
        </td>
      )}

      {/* Rating - Conditional */}
      {columnVisibility.rating && (
        <td className="py-4 px-4">
          {publication.rating && !isNaN(Number(publication.rating)) && (
            <div className="flex items-center space-x-1">
              <Star className="w-3 h-3 text-yellow-400 fill-current" />
              <span className="text-sm font-semibold text-gray-900">
                {Number(publication.rating).toFixed(1)}
              </span>
            </div>
          )}
        </td>
      )}

      {/* Links - Conditional */}
      {columnVisibility.links && (
        <td className="py-4 px-4">
          <div className="flex items-center space-x-2">
            {publication.pdf_url && (
              <a
                href={publication.pdf_url}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1 text-red-600 hover:text-red-800 hover:bg-red-50 rounded transition-colors"
                title="View PDF"
              >
                <FileText size={16} />
              </a>
            )}

            {publication.github && (
              <a
                href={publication.github}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1 text-gray-600 hover:text-gray-800 hover:bg-gray-50 rounded transition-colors"
                title="View GitHub"
              >
                <Github size={16} />
              </a>
            )}

            {publication.site && (
              <a
                href={publication.site}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded transition-colors"
                title="View Project Site"
              >
                <ExternalLink size={16} />
              </a>
            )}
          </div>
        </td>
      )}
    </tr>
  );
});

PublicationRow.displayName = 'PublicationRow';

// Memoized table body component to prevent unnecessary re-renders
const TableBody = memo(({ data, columnVisibility }: {
  data: PublicationTableItem[];
  columnVisibility: ColumnVisibility;
}) => (
  <tbody>
    {data.map((publication) => (
      <PublicationRow
        key={publication.id}
        publication={publication}
        columnVisibility={columnVisibility}
      />
    ))}
  </tbody>
));

TableBody.displayName = 'TableBody';

const PublicationsTableComponent = ({
  data,
  pagination,
  currentPage,
  onPageChange,
  searchTerm,
  onSearchChange,
  sortField,
  sortDirection,
  onSortChange,
  isFiltered,
  isLoading
}: PublicationsTableProps) => {
  const [showColumnSettings, setShowColumnSettings] = useState(false);

  // Column visibility state - title and authors always visible, others default to visible
  const [columnVisibility, setColumnVisibility] = useState<ColumnVisibility>({
    title: true,
    authors: true,
    topic: false,
    rating: true,
    links: true,
    keywords: true,
    countries: false
  });

  // Data is already filtered and sorted by backend
  const displayData = data;

  const toggleColumn = (column: keyof ColumnVisibility) => {
    if (column === 'title' || column === 'authors') return; // These are always visible
    setColumnVisibility(prev => ({
      ...prev,
      [column]: !prev[column]
    }));
  };

  // Ref for the column settings dropdown
  const columnSettingsRef = useRef<HTMLDivElement>(null);

  // Close column settings when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (columnSettingsRef.current && !columnSettingsRef.current.contains(event.target as Node)) {
        setShowColumnSettings(false);
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

  return (
    <div className="bg-white rounded-lg shadow-sm border">
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900">
            Publications ({pagination.count.toLocaleString()} total)
          </h2>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="relative flex-1 min-w-64">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="Search titles, authors, keywords..."
              value={searchTerm}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <select
            value={`${sortField}-${sortDirection}`}
            onChange={(e) => {
              const [field, direction] = e.target.value.split('-') as [SortField, SortDirection];
              onSortChange(field, direction);
            }}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="rating-desc">Sort by Rating (High to Low)</option>
            <option value="rating-asc">Sort by Rating (Low to High)</option>
            <option value="title-asc">Sort by Title (A to Z)</option>
            <option value="title-desc">Sort by Title (Z to A)</option>
          </select>

          <div className="relative" ref={columnSettingsRef}>
            <button
              onClick={() => setShowColumnSettings(!showColumnSettings)}
              className="flex items-center px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <Settings size={16} className="mr-2" />
              Columns
            </button>

            {showColumnSettings && (
              <div className="absolute right-0 top-full mt-2 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
                <div className="p-4">
                  <h4 className="font-medium text-gray-900 mb-3">Show/Hide Columns</h4>
                  <div className="space-y-2">
                    {Object.entries(columnVisibility).map(([key, visible]) => {
                      const isRequired = key === 'title' || key === 'authors';
                      const label = key.charAt(0).toUpperCase() + key.slice(1);

                      return (
                        <label key={key} className="flex items-center space-x-2">
                          <div
                            className={`w-4 h-4 rounded flex items-center justify-center border ${
                              visible
                                ? 'bg-blue-600 border-blue-600 text-white'
                                : 'border-gray-300 bg-white'
                            } ${isRequired ? 'opacity-50' : 'cursor-pointer'}`}
                            onClick={() => !isRequired && toggleColumn(key as keyof ColumnVisibility)}
                          >
                            {visible && <span className="text-xs">✓</span>}
                          </div>
                          <span className={`text-sm ${isRequired ? 'text-gray-500' : 'text-gray-700'}`}>
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
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Title</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Authors</th>
                {columnVisibility.topic && (
                  <th className="text-left py-3 px-4 font-semibold text-gray-900">Topic</th>
                )}
                {columnVisibility.rating && (
                  <th className="text-left py-3 px-4 font-semibold text-gray-900">Rating</th>
                )}
                {columnVisibility.links && (
                  <th className="text-left py-3 px-4 font-semibold text-gray-900">Links</th>
                )}
              </tr>
            </thead>
            <TableBody
              data={displayData}
              columnVisibility={columnVisibility}
            />
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center space-x-2 mt-6">
            <button
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="flex items-center px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft size={16} className="mr-1" />
              Previous
            </button>

            <div className="flex space-x-1">
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const page = Math.max(1, Math.min(totalPages - 4, currentPage - 2)) + i;
                if (page > totalPages) return null;

                return (
                  <button
                    key={page}
                    onClick={() => onPageChange(page)}
                    className={`px-3 py-2 text-sm rounded-lg ${
                      currentPage === page
                        ? 'bg-blue-600 text-white'
                        : 'border border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    {page}
                  </button>
                );
              })}
            </div>

            <button
              onClick={() => onPageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="flex items-center px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
              <ChevronRight size={16} className="ml-1" />
            </button>
          </div>
        )}

        {/* Results Info */}
        <div className="text-sm text-gray-600 text-center mt-4">
          Showing {displayData.length} of {pagination.count.toLocaleString()} publications
          {isFiltered ? ' (filtered)' : ''}
        </div>
      </div>
    </div>
  );
};

PublicationsTableComponent.displayName = 'PublicationsTable';

// Memoized export to prevent unnecessary re-renders
export const PublicationsTable = memo(PublicationsTableComponent);