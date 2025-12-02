import React, { useState, useMemo } from 'react';
import Header from '@/shared/components/layout/Header';
import { Sparkles, Filter, Search, AlertCircle } from 'lucide-react';
import { useInstances } from '@/features/conference/hooks/useConference';
import { Button } from '@/shared/components/ui/button';
import { datasetService, SemanticSearchResult } from '../services/datasetService';
import { PublicationsTableEnhanced } from '@/features/conference/components/PublicationsTableEnhanced';
import { PublicationTableItem } from '@/features/conference/types';
import { conferenceService } from '@/features/conference/services/ConferenceService';

export default function DatasetPage() {
    // State
    const [selectedVenue, setSelectedVenue] = useState<string>('');
    const [selectedYear, setSelectedYear] = useState<number | undefined>();
    const [searchQuery, setSearchQuery] = useState('');
    const [isSearching, setIsSearching] = useState(false);
    const [searchResults, setSearchResults] = useState<SemanticSearchResult[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [searchMetadata, setSearchMetadata] = useState<{ processing_time_ms: number; llm_model: string } | null>(null);

    // Data hooks
    const { data: instances, isLoading: instancesLoading } = useInstances();

    // Derived data for filters
    const venues = useMemo(() => {
        if (!instances) return [];
        const uniqueVenues = new Set(instances.map(i => i.venue.name));
        return Array.from(uniqueVenues).sort();
    }, [instances]);

    const years = useMemo(() => {
        if (!instances) return [];
        const uniqueYears = new Set(instances.map(i => i.year));
        return Array.from(uniqueYears).sort((a, b) => b - a);
    }, [instances]);

    // Handle search
    const handleSearch = async () => {
        if (!searchQuery.trim()) return;
        if (!selectedVenue && !selectedYear) {
            setError('Please select at least one filter (Venue or Year) to narrow down the dataset.');
            return;
        }

        setIsSearching(true);
        setError(null);
        setSearchResults([]);
        setSearchMetadata(null);

        try {
            // 1. Fetch relevant publications based on filters
            // We need to get IDs first. This might be heavy if the dataset is large.
            // We'll fetch instances matching the filters first.
            const matchingInstances = instances?.filter(i => {
                const matchVenue = selectedVenue ? i.venue.name === selectedVenue : true;
                const matchYear = selectedYear ? i.year === selectedYear : true;
                return matchVenue && matchYear;
            }) || [];

            if (matchingInstances.length === 0) {
                setError('No conferences found matching your filters.');
                setIsSearching(false);
                return;
            }

            // Fetch publications for these instances
            // Note: This could be optimized if the backend supported bulk fetching or filtering by venue/year directly
            // For now, we'll fetch for each instance (limited to avoid too many requests)
            // LIMIT: Let's limit to top 5 instances if too many, or warn user?
            // For this implementation, let's assume we fetch all publications for the matching instances.
            // But we need to be careful about the 1000 ID limit of the semantic search API.

            let allPublicationIds: string[] = [];

            // We'll fetch publications for each instance. 
            // To avoid N+1, ideally we'd have a better API. 
            // Let's try to fetch with a reasonable page size for each instance and collect IDs.
            // OR, maybe we can just fetch the first page of each? No, we need all IDs for semantic search to work effectively.

            // WORKAROUND: For now, let's just use the first matching instance if multiple are found, 
            // or ask the user to be more specific if the count is high.
            // But the requirement says "filter year OR conference".

            // Let's try to fetch publications for all matching instances.
            const promises = matchingInstances.map(instance =>
                conferenceService.getPublications({ instance: instance.instance_id, page_size: 1000 })
            );

            const responses = await Promise.all(promises);

            responses.forEach(res => {
                if (res.results) {
                    allPublicationIds.push(...res.results.map(p => p.id));
                }
            });

            if (allPublicationIds.length === 0) {
                setError('No publications found for the selected filters.');
                setIsSearching(false);
                return;
            }

            if (allPublicationIds.length > 1000) {
                // Truncate to 1000 for now as per API limit
                allPublicationIds = allPublicationIds.slice(0, 1000);
                // You might want to show a warning here
            }

            // 2. Call Semantic Search API
            const response = await datasetService.semanticSearch({
                publication_ids: allPublicationIds,
                query: searchQuery,
                topk: 20
            });

            if (response.success) {
                setSearchResults(response.results);
                setSearchMetadata(response.metadata);
            } else {
                setError(response.error || 'Semantic search failed.');
            }

        } catch (err) {
            console.error('Search error:', err);
            setError('An error occurred during search.');
        } finally {
            setIsSearching(false);
        }
    };

    return (
        <div className="min-h-screen bg-background flex flex-col">
            <Header />

            <main className="flex-grow pt-[var(--header-height)]">
                {/* Header Section */}
                <section className="relative bg-white border-b border-gray-100">
                    <div className="absolute inset-0 bg-gradient-to-b from-gray-50/50 to-white/20 pointer-events-none" />
                    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-12 relative z-10">
                        <div className="max-w-3xl">
                            <div className="flex items-center gap-2 mb-4">
                                <span className="px-3 py-1 rounded-full bg-purple-50 text-xs font-medium text-purple-600 flex items-center gap-1">
                                    <Sparkles className="w-3 h-3" />
                                    Semantic Search
                                </span>
                            </div>
                            <h1 className="text-4xl font-bold text-[#1E1E1E] tracking-tight mb-4">
                                Dataset Explorer
                            </h1>
                            <p className="text-lg text-gray-500 leading-relaxed">
                                Filter conferences and use natural language to find the most relevant papers.
                            </p>
                        </div>
                    </div>
                </section>

                <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">

                        {/* Filters Sidebar */}
                        <div className="lg:col-span-1 space-y-6">
                            <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                                <div className="flex items-center gap-2 mb-4 text-[#1E1E1E] font-semibold">
                                    <Filter className="w-4 h-4" />
                                    <h3>Filters</h3>
                                </div>

                                <div className="space-y-4">
                                    {/* Venue Filter */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Conference</label>
                                        <select
                                            className="w-full p-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-black/5 focus:border-black outline-none transition-all"
                                            value={selectedVenue}
                                            onChange={(e) => setSelectedVenue(e.target.value)}
                                            disabled={instancesLoading}
                                        >
                                            <option value="">All Conferences</option>
                                            {venues.map(venue => (
                                                <option key={venue} value={venue}>{venue}</option>
                                            ))}
                                        </select>
                                    </div>

                                    {/* Year Filter */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Year</label>
                                        <select
                                            className="w-full p-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-black/5 focus:border-black outline-none transition-all"
                                            value={selectedYear || ''}
                                            onChange={(e) => setSelectedYear(e.target.value ? Number(e.target.value) : undefined)}
                                            disabled={instancesLoading}
                                        >
                                            <option value="">All Years</option>
                                            {years.map(year => (
                                                <option key={year} value={year}>{year}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Main Content */}
                        <div className="lg:col-span-3 space-y-6">

                            {/* Search Bar */}
                            <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                                <div className="relative">
                                    <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                                    <input
                                        type="text"
                                        placeholder="Describe what you are looking for (e.g., 'papers about transformer efficiency in mobile devices')..."
                                        className="w-full pl-12 pr-4 py-4 border border-gray-200 rounded-lg text-lg focus:ring-2 focus:ring-black/5 focus:border-black outline-none transition-all shadow-sm"
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                                    />
                                    <div className="absolute right-2 top-1/2 transform -translate-y-1/2">
                                        <Button
                                            onClick={handleSearch}
                                            disabled={isSearching || !searchQuery.trim()}
                                            className="bg-black text-white hover:bg-gray-800"
                                        >
                                            {isSearching ? 'Searching...' : 'Search'}
                                        </Button>
                                    </div>
                                </div>
                                {searchMetadata && (
                                    <div className="mt-3 text-xs text-gray-400 flex justify-end gap-4">
                                        <span>Model: {searchMetadata.llm_model}</span>
                                        <span>Time: {searchMetadata.processing_time_ms}ms</span>
                                    </div>
                                )}
                            </div>

                            {/* Error Message */}
                            {error && (
                                <div className="bg-red-50 border border-red-100 text-red-700 p-4 rounded-lg flex items-center gap-2">
                                    <AlertCircle className="w-5 h-5" />
                                    {error}
                                </div>
                            )}

                            {/* Results */}
                            {searchResults.length > 0 && (
                                <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                                    <PublicationsTableEnhanced
                                        data={searchResults}
                                        pagination={{ count: searchResults.length, next: null, previous: null }}
                                        currentPage={1}
                                        onPageChange={() => { }}
                                        searchTerm=""
                                        onSearchChange={() => { }}
                                        sortField="rating"
                                        sortDirection="desc"
                                        onSortChange={() => { }}
                                        isFiltered={false}
                                        isLoading={false}
                                    />
                                </div>
                            )}

                            {/* Empty State */}
                            {!isSearching && searchResults.length === 0 && !error && (
                                <div className="text-center py-20 text-gray-400">
                                    <Sparkles className="w-12 h-12 mx-auto mb-4 opacity-20" />
                                    <p className="text-lg">Select filters and enter a query to start semantic search.</p>
                                </div>
                            )}

                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
