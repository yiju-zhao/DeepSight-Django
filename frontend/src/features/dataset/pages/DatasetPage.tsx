import React, { useState, useMemo, useEffect, useRef } from 'react';
import Header from '@/shared/components/layout/Header';
import { Sparkles, Filter, Search, AlertCircle, Loader2 } from 'lucide-react';
import { useInstances } from '@/features/conference/hooks/useConference';
import { Button } from '@/shared/components/ui/button';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/shared/components/ui/select';
import { datasetService, SemanticSearchResult, StreamProgressEvent } from '../services/datasetService';
import { PublicationsTableEnhanced } from '@/features/conference/components/PublicationsTableEnhanced';
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

    // Streaming state
    const [streamProgress, setStreamProgress] = useState<number>(0);
    const [streamStatus, setStreamStatus] = useState<string | null>(null);
    const [batchCount, setBatchCount] = useState<{ current: number; total: number }>({ current: 0, total: 0 });
    const eventSourceRef = useRef<EventSource | null>(null);

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

    // Cleanup EventSource on unmount
    useEffect(() => {
        return () => {
            if (eventSourceRef.current) {
                eventSourceRef.current.close();
                eventSourceRef.current = null;
            }
        };
    }, []);

    // Handle streaming search
    const handleStreamingSearch = async () => {
        if (!searchQuery.trim()) return;
        if (!selectedVenue && !selectedYear) {
            setError('Please select at least one filter (Venue or Year) to narrow down the dataset.');
            return;
        }

        setIsSearching(true);
        setError(null);
        setSearchResults([]);
        setStreamProgress(0);
        setStreamStatus('Initializing search...');
        setBatchCount({ current: 0, total: 0 });

        try {
            // 1. Fetch relevant publication IDs based on filters
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

            // Fetch all publication IDs
            const promises = matchingInstances.map(instance =>
                conferenceService.getPublications({ instance: instance.instance_id, page_size: 10000 })
            );

            const responses = await Promise.all(promises);
            let allPublicationIds: string[] = [];
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

            setStreamStatus(`Found ${allPublicationIds.length} publications. Starting semantic search...`);

            // 2. Start streaming search
            const streamResponse = await datasetService.startStreamingSearch({
                publication_ids: allPublicationIds,
                query: searchQuery,
                topk: 50, // Get top 50 results
            });

            if (!streamResponse.success) {
                setError('Failed to start streaming search.');
                setIsSearching(false);
                return;
            }

            // 3. Connect to SSE stream
            const eventSource = datasetService.connectToStream(streamResponse.job_id);
            eventSourceRef.current = eventSource;

            eventSource.onmessage = (event) => {
                try {
                    const data: StreamProgressEvent = JSON.parse(event.data);

                    switch (data.type) {
                        case 'connected':
                            setStreamStatus('Connected to stream');
                            break;

                        case 'started':
                            setStreamStatus(`Processing ${data.total} publications...`);
                            if (data.total_batches) {
                                setBatchCount({ current: 0, total: data.total_batches });
                            }
                            break;

                        case 'batch':
                            if (data.batch_num && data.total_batches) {
                                setBatchCount({ current: data.batch_num, total: data.total_batches });
                                setStreamStatus(`Processing batch ${data.batch_num}/${data.total_batches}...`);
                            }
                            if (data.progress) {
                                setStreamProgress(data.progress * 100);
                            }
                            if (data.batch_results) {
                                // Incrementally add results
                                setSearchResults(prev => [...prev, ...data.batch_results!]);
                            }
                            break;

                        case 'complete':
                            setStreamStatus('Search completed!');
                            setStreamProgress(100);
                            if (data.final_results) {
                                setSearchResults(data.final_results);
                            }
                            setIsSearching(false);
                            eventSource.close();
                            eventSourceRef.current = null;
                            break;

                        case 'error':
                            setError(data.detail || 'Search failed');
                            setIsSearching(false);
                            eventSource.close();
                            eventSourceRef.current = null;
                            break;
                    }
                } catch (err) {
                    console.error('Failed to parse SSE message:', err);
                }
            };

            eventSource.onerror = (err) => {
                console.error('SSE error:', err);
                setError('Connection error. Please try again.');
                setIsSearching(false);
                eventSource.close();
                eventSourceRef.current = null;
            };

        } catch (err) {
            console.error('Search error:', err);
            setError('An error occurred during search.');
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
                                        <Select
                                            value={selectedVenue || "ALL"}
                                            onValueChange={(value) => setSelectedVenue(value === "ALL" ? "" : value)}
                                            disabled={instancesLoading || isSearching}
                                        >
                                            <SelectTrigger>
                                                <SelectValue placeholder="All Conferences" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="ALL">All Conferences</SelectItem>
                                                {venues.map(venue => (
                                                    <SelectItem key={venue} value={venue}>{venue}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    {/* Year Filter */}
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Year</label>
                                        <Select
                                            value={selectedYear ? selectedYear.toString() : "ALL"}
                                            onValueChange={(value) => setSelectedYear(value === "ALL" ? undefined : Number(value))}
                                            disabled={instancesLoading || isSearching}
                                        >
                                            <SelectTrigger>
                                                <SelectValue placeholder="All Years" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="ALL">All Years</SelectItem>
                                                {years.map(year => (
                                                    <SelectItem key={year} value={year.toString()}>{year}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
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
                                        onKeyDown={(e) => e.key === 'Enter' && !isSearching && handleStreamingSearch()}
                                        disabled={isSearching}
                                    />
                                    <div className="absolute right-2 top-1/2 transform -translate-y-1/2">
                                        <Button
                                            onClick={handleStreamingSearch}
                                            disabled={isSearching || !searchQuery.trim()}
                                            className="bg-black text-white hover:bg-gray-800 flex items-center gap-2"
                                        >
                                            {isSearching && <Loader2 className="w-4 h-4 animate-spin" />}
                                            {isSearching ? 'Searching...' : 'Search'}
                                        </Button>
                                    </div>
                                </div>
                            </div>

                            {/* Progress Indicator */}
                            {isSearching && (
                                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between text-sm">
                                            <span className="text-gray-700 font-medium">{streamStatus}</span>
                                            <span className="text-gray-500">
                                                {batchCount.total > 0 && `Batch ${batchCount.current}/${batchCount.total}`}
                                            </span>
                                        </div>
                                        <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                                            <div
                                                className="bg-purple-600 h-full transition-all duration-300 ease-out"
                                                style={{ width: `${streamProgress}%` }}
                                            />
                                        </div>
                                        <p className="text-xs text-gray-500">
                                            {searchResults.length} results found so far...
                                        </p>
                                    </div>
                                </div>
                            )}

                            {/* Error Message */}
                            {error && (
                                <div className="bg-red-50 border border-red-100 text-red-700 p-4 rounded-lg flex items-center gap-2">
                                    <AlertCircle className="w-5 h-5" />
                                    {error}
                                </div>
                            )}

                            {/* Results Table */}
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
