import React, { useState, useMemo } from 'react';
import { Mic, Image as ImageIcon, Sparkles, BookOpen } from 'lucide-react';
import { SessionTypeCard } from './SessionTypeCard';
import { SessionTypeFilter } from './SessionTypeFilter';
import PublicationsTableEnhanced from './PublicationsTableEnhanced';
import { usePublications } from '../hooks/useConference';

interface SessionTypeViewProps {
  instanceId: number;
}

// Map session types to icons
const SESSION_ICONS = {
  'Oral': Mic,
  'Poster': ImageIcon,
  'Spotlight': Sparkles,
  'Workshop': BookOpen,
};

const SESSION_COLORS = {
  'Oral': '#CE0E2D',
  'Poster': '#1E1E1E',
  'Spotlight': '#666666',
  'Workshop': '#000000',
};

export const SessionTypeView: React.FC<SessionTypeViewProps> = ({ instanceId }) => {
  const [selectedSessionTypes, setSelectedSessionTypes] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState<'rating' | 'title'>('rating');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  // Fetch all publications for this instance to get session statistics
  const { data: allPublicationsData, isLoading: isLoadingAll } = usePublications({
    instance: instanceId,
    page: 1,
    page_size: 1000, // Get all to calculate statistics
  });

  // Fetch filtered publications based on selected session types
  const sessionFilter = selectedSessionTypes.length > 0 ? selectedSessionTypes.join(',') : undefined;
  const { data: filteredPublicationsData, isLoading: isLoadingFiltered } = usePublications({
    instance: instanceId,
    page: currentPage,
    page_size: 20,
    search: searchTerm || undefined,
    ordering: `${sortDirection === 'desc' ? '-' : ''}${sortField}`,
    // Note: Backend would need to support comma-separated session filter or we filter client-side
  });

  // Calculate session type statistics
  const sessionStats = useMemo(() => {
    if (!allPublicationsData?.results) return [];

    const stats = new Map<string, { count: number; totalRating: number; ratingCount: number }>();

    allPublicationsData.results.forEach((pub) => {
      const session = pub.session || 'Unknown';
      if (session === 'reject') return; // Skip rejected

      if (!stats.has(session)) {
        stats.set(session, { count: 0, totalRating: 0, ratingCount: 0 });
      }

      const stat = stats.get(session)!;
      stat.count++;
      if (pub.rating !== undefined && pub.rating !== null) {
        stat.totalRating += pub.rating;
        stat.ratingCount++;
      }
    });

    const total = allPublicationsData.results.filter(p => p.session !== 'reject').length;

    return Array.from(stats.entries())
      .map(([type, data]) => ({
        type,
        count: data.count,
        percentage: (data.count / total) * 100,
        avgRating: data.ratingCount > 0 ? data.totalRating / data.ratingCount : undefined,
      }))
      .sort((a, b) => b.count - a.count); // Sort by count descending
  }, [allPublicationsData]);

  // Filter publications client-side if backend doesn't support it
  const displayPublications = useMemo(() => {
    if (!filteredPublicationsData?.results) return [];

    if (selectedSessionTypes.length === 0) {
      return filteredPublicationsData.results;
    }

    return filteredPublicationsData.results.filter(pub =>
      selectedSessionTypes.includes(pub.session || 'Unknown')
    );
  }, [filteredPublicationsData, selectedSessionTypes]);

  const handleSessionTypeToggle = (type: string) => {
    setSelectedSessionTypes(prev =>
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
    setCurrentPage(1); // Reset to first page when filter changes
  };

  const handleClearAllFilters = () => {
    setSelectedSessionTypes([]);
    setCurrentPage(1);
  };

  const handleSortChange = (field: 'rating' | 'title', direction: 'asc' | 'desc') => {
    setSortField(field);
    setSortDirection(direction);
    setCurrentPage(1);
  };

  if (isLoadingAll) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-black border-r-transparent mb-4"></div>
          <p className="text-sm text-[#666666]">Loading session data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header - HUAWEI Style */}
      <div>
        <h2 className="text-[28px] font-bold text-[#1E1E1E] leading-tight">Session Types</h2>
        <p className="text-sm text-[#666666] mt-2">
          Explore publications by presentation type and session format
        </p>
      </div>

      {/* Session Type Cards - 4 Column Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {sessionStats.map((stat) => {
          const Icon = SESSION_ICONS[stat.type as keyof typeof SESSION_ICONS] || BookOpen;
          const isActive = selectedSessionTypes.includes(stat.type);

          return (
            <SessionTypeCard
              key={stat.type}
              icon={Icon}
              sessionType={stat.type}
              count={stat.count}
              percentage={stat.percentage}
              avgRating={stat.avgRating}
              isActive={isActive}
              onClick={() => handleSessionTypeToggle(stat.type)}
            />
          );
        })}
      </div>

      {/* Filter Bar */}
      {sessionStats.length > 0 && (
        <div className="bg-white rounded-lg shadow-[rgba(0,0,0,0.08)_0px_8px_12px] border border-[#E3E3E3] p-4">
          <SessionTypeFilter
            sessionTypes={sessionStats.map(s => ({ type: s.type, count: s.count }))}
            selectedTypes={selectedSessionTypes}
            onToggle={handleSessionTypeToggle}
            onClearAll={handleClearAllFilters}
          />
        </div>
      )}

      {/* Publications List */}
      <div>
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold text-[#1E1E1E]">
              Publications
            </h3>
            {selectedSessionTypes.length > 0 && (
              <p className="text-sm text-[#666666] mt-1">
                Filtered by: {selectedSessionTypes.join(', ')}
              </p>
            )}
          </div>
          <div className="text-sm font-medium text-[#666666]">
            {displayPublications.length} result{displayPublications.length !== 1 ? 's' : ''}
          </div>
        </div>

        <PublicationsTableEnhanced
          data={displayPublications}
          pagination={{
            count: filteredPublicationsData?.count || 0,
            next: filteredPublicationsData?.next || null,
            previous: filteredPublicationsData?.previous || null,
          }}
          currentPage={currentPage}
          onPageChange={setCurrentPage}
          searchTerm={searchTerm}
          onSearchChange={setSearchTerm}
          sortField={sortField}
          sortDirection={sortDirection}
          onSortChange={handleSortChange}
          isFiltered={selectedSessionTypes.length > 0 || !!searchTerm}
          isLoading={isLoadingFiltered}
          onViewDetails={(publication) => {
            console.log('View details for:', publication.title);
          }}
        />
      </div>
    </div>
  );
};
