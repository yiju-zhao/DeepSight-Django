import { useState } from 'react';
import { PublicationTableItem, PaginationInfo } from '../types';
import {
  ExternalLink,
  Github,
  FileText,
  Star,
  Search,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

interface PublicationsTableProps {
  data: PublicationTableItem[];
  pagination: PaginationInfo;
  currentPage: number;
  onPageChange: (page: number) => void;
  isLoading?: boolean;
}

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

export function PublicationsTable({
  data,
  pagination,
  currentPage,
  onPageChange,
  isLoading
}: PublicationsTableProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterTopic, setFilterTopic] = useState('');
  const [filterSession, setFilterSession] = useState('');

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  // Get unique values for filters
  const uniqueTopics = [...new Set(data.map(item => item.research_topic))].filter(Boolean);
  const uniqueSessions = [...new Set(data.map(item => item.session))].filter(Boolean);

  // Filter data
  const filteredData = data.filter(item => {
    const matchesSearch = searchTerm === '' ||
      item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.authors.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.keywords.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesTopic = filterTopic === '' || item.research_topic === filterTopic;
    const matchesSession = filterSession === '' || item.session === filterSession;

    return matchesSearch && matchesTopic && matchesSession;
  });

  const totalPages = Math.ceil(pagination.count / 20);

  return (
    <div className="bg-white rounded-lg shadow-sm border">
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900">
            Publications ({pagination.count.toLocaleString()} total)
          </h2>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="relative flex-1 min-w-64">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="Search titles, authors, keywords..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <select
            value={filterTopic}
            onChange={(e) => setFilterTopic(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">All Topics</option>
            {uniqueTopics.map(topic => (
              <option key={topic} value={topic}>{topic}</option>
            ))}
          </select>

          <select
            value={filterSession}
            onChange={(e) => setFilterSession(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">All Sessions</option>
            {uniqueSessions.map(session => (
              <option key={session} value={session}>{session}</option>
            ))}
          </select>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Title</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Authors</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Topic</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Session</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Rating</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Links</th>
              </tr>
            </thead>
            <tbody>
              {filteredData.map((publication) => (
                <tr
                  key={publication.id}
                  className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                >
                  <td className="py-4 px-4">
                    <div className="space-y-1">
                      <div className="font-medium text-gray-900 text-sm">
                        {publication.title}
                      </div>
                      <div className="text-xs text-gray-600 line-clamp-2">
                        {(() => {
                          // Use split logic for keywords (semicolon-separated)
                          const keywords = publication.keywords_list ||
                            (publication.keywords ?
                              publication.keywords.split(';')
                                .map(k => k.trim())
                                .filter(k => k.length > 0)
                              : []
                            );
                          return keywords.slice(0, 3).join(', ');
                        })()}
                      </div>
                    </div>
                  </td>

                  <td className="py-4 px-4">
                    <div className="space-y-2">
                      <div className="text-sm text-gray-900">
                        {publication.authors_list ? (
                          <>
                            {publication.authors_list.slice(0, 3).map((author, index) => (
                              <span key={index} className="inline-block">
                                {author}
                                {index < Math.min(publication.authors_list!.length - 1, 2) && ', '}
                              </span>
                            ))}
                            {publication.authors_list.length > 3 && (
                              <span className="text-gray-500"> +{publication.authors_list.length - 3} more</span>
                            )}
                          </>
                        ) : (
                          <>
                            {publication.authors.split(',').slice(0, 3).join(', ')}
                            {publication.authors.split(',').length > 3 && '...'}
                          </>
                        )}
                      </div>
                      {publication.aff_country_unique && (
                        <div className="flex flex-wrap gap-1">
                          {(() => {
                            // Always use split logic to handle malformed data
                            const countries = publication.countries_list ||
                              (publication.aff_country_unique ?
                                publication.aff_country_unique.split(',')
                                  .map(c => c.trim())
                                  .filter(c => c.length > 0)
                                : []
                              );

                            return (
                              <>
                                {countries.slice(0, 3).map((country, index) => (
                                  <span key={index} className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                                    {country}
                                  </span>
                                ))}
                                {countries.length > 3 && (
                                  <span className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">
                                    +{countries.length - 3}
                                  </span>
                                )}
                              </>
                            );
                          })()}
                        </div>
                      )}
                    </div>
                  </td>

                  <td className="py-4 px-4">
                    <span className="text-sm text-gray-900">
                      {publication.research_topic}
                    </span>
                  </td>

                  <td className="py-4 px-4">
                    {publication.session && (
                      <span className={`inline-block px-2 py-1 text-xs rounded ${
                        publication.session === 'Oral'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-blue-100 text-blue-800'
                      }`}>
                        {publication.session}
                      </span>
                    )}
                  </td>

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
                </tr>
              ))}
            </tbody>
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
          Showing {filteredData.length} of {pagination.count.toLocaleString()} publications
          {searchTerm || filterTopic || filterSession ? ' (filtered)' : ''}
        </div>
      </div>
    </div>
  );
}