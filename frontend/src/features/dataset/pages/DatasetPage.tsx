import React, { useState, useMemo, useEffect, useRef } from 'react';
import Header from '@/shared/components/layout/Header';
import { Sparkles, Search, AlertCircle, Loader2, X } from 'lucide-react';
import { useInstances } from '@/features/conference/hooks/useConference';
import { Button } from '@/shared/components/ui/button';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/shared/components/ui/select';

import { datasetService, StreamProgressEvent, PublicationIdWithScore } from '../services/datasetService';
import { PublicationsTableEnhanced } from '@/features/conference/components/PublicationsTableEnhanced';
import { conferenceService } from '@/features/conference/services/ConferenceService';
import { SearchFilters } from '../components/SearchFilters';
import type { PublicationTableItem } from '@/features/conference/types';

export default function DatasetPage() {
    // UI State
    const [hasSearched, setHasSearched] = useState(false);
    const [isSearching, setIsSearching] = useState(false);

    // Filter State
    const [selectedVenue, setSelectedVenue] = useState<string>('');
    const [selectedYear, setSelectedYear] = useState<number | undefined>();
    const [topk, setTopk] = useState<number>(20);
    const [searchQuery, setSearchQuery] = useState('');

    // Search Results State
    const [publicationIds, setPublicationIds] = useState<string[]>([]);
    const [publications, setPublications] = useState<PublicationTableItem[]>([]);
    const [isFetchingPublications, setIsFetchingPublications] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Streaming State
    const [streamProgress, setStreamProgress] = useState<number>(0);
    const [streamStatus, setStreamStatus] = useState<string | null>(null);
    const [batchCount, setBatchCount] = useState<{ current: number; total: number }>({ current: 0, total: 0 });
    const eventSourceRef = useRef<EventSource | null>(null);
    const fetchedPublicationIdsRef = useRef<Set<string>>(new Set());

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

    // Check if filters are active
    const hasActiveFilters = selectedVenue || selectedYear;

    // Cleanup EventSource on unmount
    useEffect(() => {
        return () => {
            if (eventSourceRef.current) {
                eventSourceRef.current.close();
                eventSourceRef.current = null;
            }
        };
    }, []);

    // Incrementally fetch publication details for new IDs only
    useEffect(() => {
        const fetchMissingPublications = async () => {
            if (publicationIds.length === 0) {
                return;
            }

            const missingIds = publicationIds.filter(
                id => !fetchedPublicationIdsRef.current.has(id),
            );

            if (missingIds.length === 0) {
                return;
            }

            setIsFetchingPublications(true);
            try {
                const CHUNK_SIZE = 100;

                for (let i = 0; i < missingIds.length; i += CHUNK_SIZE) {
                    const chunk = missingIds.slice(i, i + CHUNK_SIZE);
                    const newPublications = await datasetService.fetchPublicationsByIds(chunk);

                    setPublications(prev => {
                        // Only append truly new items, keep existing objects
                        const existingIds = new Set(prev.map(pub => pub.id));
                        const toAppend: PublicationTableItem[] = [];
                        newPublications.forEach(pub => {
                            if (!existingIds.has(pub.id)) {
                                toAppend.push(pub);
                                fetchedPublicationIdsRef.current.add(pub.id);
                            }
                        });

                        return [...prev, ...toAppend];
                    });
                }
            } catch (e) {
                console.error('Failed to fetch publications by IDs:', e);
            } finally {
                setIsFetchingPublications(false);
            }
        };

        fetchMissingPublications();
    }, [publicationIds]);

    // Handle streaming search
    const handleStreamingSearch = async () => {
        if (!searchQuery.trim()) return;
        if (!selectedVenue && !selectedYear) {
            setError('Please select at least one filter (Conference or Year) to narrow down the dataset.');
            return;
        }

        // Mark that a search has been initiated (triggers UI transition)
        setHasSearched(true);
        setIsSearching(true);
        setError(null);
        setPublicationIds([]); // Clear previous results
        setPublications([]);
        fetchedPublicationIdsRef.current = new Set();
        setStreamProgress(0);
        setStreamStatus('Initializing search...');
        setBatchCount({ current: 0, total: 0 });

        try {
            // Helper: fetch all publications for a single instance across all pages
            const fetchAllPublicationIdsForInstance = async (instanceId: number): Promise<string[]> => {
                let page = 1;
                let hasNext = true;
                const ids: string[] = [];

                while (hasNext) {
                    const res = await conferenceService.getPublications({
                        instance: instanceId,
                        page,
                        page_size: 1000,
                    });

                    if (res.results && res.results.length > 0) {
                        ids.push(...res.results.map(p => p.id));
                    }

                    // DRF-style pagination: if next is null/undefined, we've reached the last page
                    hasNext = !!res.next;
                    page += 1;
                }

                return ids;
            };

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

            // Fetch all publication IDs across all pages for each matching instance
            const idArrays = await Promise.all(
                matchingInstances.map(instance => fetchAllPublicationIdsForInstance(instance.instance_id))
            );
            const allPublicationIds = idArrays.flat();

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
                topk, // Use user-configurable top-k (default 20)
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

                    // 🔍 Debug logging to track SSE events
                    console.log('[SSE Event]', data.type, {
                        batch_num: data.batch_num,
                        total_batches: data.total_batches,
                        progress: data.progress,
                        batch_result_count: data.batch_result_ids?.length,
                        final_result_count: data.final_result_ids?.length,
                    });

                    switch (data.type) {
                        case 'connected':
                            console.log('[SSE] Connected to search stream');
                            setStreamStatus('Connected to stream');
                            break;

                        case 'started':
                            console.log('[Started Event]', {
                                total: data.total,
                                total_batches: data.total_batches,
                            });
                            setStreamStatus(`Processing ${data.total} publications...`);
                            if (data.total_batches !== undefined && data.total_batches > 0) {
                                setBatchCount({ current: 0, total: data.total_batches });
                            } else {
                                console.warn(
                                    '[Started Event] Missing or invalid total_batches:',
                                    data.total_batches,
                                );
                            }
                            break;

                        case 'batch':
                            console.log('[Batch Event]', {
                                batch_num: data.batch_num,
                                total_batches: data.total_batches,
                                processed: data.processed,
                                total: data.total,
                                result_count: data.batch_result_ids?.length,
                            });

                            if (data.batch_num !== undefined && data.total_batches !== undefined) {
                                setBatchCount({ current: data.batch_num, total: data.total_batches });
                                setStreamStatus(`Processing batch ${data.batch_num}/${data.total_batches}...`);
                            } else {
                                console.warn('[Batch Event] Missing batch_num or total_batches:', {
                                    batch_num: data.batch_num,
                                    total_batches: data.total_batches,
                                });
                                // Fallback: show progress percentage
                                setStreamStatus(`Processing... ${Math.round((data.progress || 0) * 100)}%`);
                            }

                            if (data.progress !== undefined) {
                                setStreamProgress(data.progress * 100);
                            }
                            // Accumulate publication IDs progressively
                            if (data.batch_result_ids && data.batch_result_ids.length > 0) {
                                setPublicationIds(prev => {
                                    const newIds = data.batch_result_ids!.map(r => r.id);
                                    // Deduplicate: only add IDs that don't already exist
                                    const existingIds = new Set(prev);
                                    const uniqueNewIds = newIds.filter(id => !existingIds.has(id));
                                    console.log(
                                        `[Batch] Adding ${uniqueNewIds.length} new IDs (total: ${
                                            prev.length + uniqueNewIds.length
                                        })`,
                                    );
                                    return [...prev, ...uniqueNewIds];
                                });
                            }
                            break;

                        case 'complete':
                            console.log('[Complete Event]', {
                                final_result_count: data.final_result_ids?.length,
                                current_accumulated: publicationIds.length,
                            });
                            setStreamStatus('Search completed!');
                            setStreamProgress(100);
                            // Don't replace accumulated IDs - backend already sends final ranked results progressively
                            // Only update if final_result_ids differ significantly (e.g., final ranking applied)
                            if (data.final_result_ids && data.final_result_ids.length > 0) {
                                const finalIds = data.final_result_ids.map(r => r.id);
                                setPublicationIds(prev => {
                                    // If final results are different, use them (final ranking applied)
                                    if (finalIds.length !== prev.length) {
                                        console.log(
                                            `[Complete] Updating with ${finalIds.length} final ranked results`,
                                        );
                                        return finalIds;
                                    }
                                    // Otherwise keep accumulated results (already in correct order)
                                    console.log(`[Complete] Keeping ${prev.length} accumulated results`);
                                    return prev;
                                });
                            }
                            setIsSearching(false);
                            eventSource.close();
                            eventSourceRef.current = null;
                            break;

                        case 'error':
                            console.error('[Error Event]', data.detail);
                            setError(data.detail || 'Search failed');
                            setIsSearching(false);
                            eventSource.close();
                            eventSourceRef.current = null;
                            break;
                    }
                } catch (err) {
                    console.error('[SSE] Failed to parse message:', err, event.data);
                }
            };

            eventSource.onerror = (err) => {
                console.error('[SSE Error]', err);
                console.log('[SSE ReadyState]', eventSource.readyState);

                // Only treat as error if connection failed (not normal completion)
                if (eventSource.readyState === EventSource.CLOSED && !isSearching) {
                    // Normal completion, not an error
                    console.log('[SSE] Connection closed normally');
                    return;
                }

                // Actual error occurred
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

    // Reset search state
    const handleReset = () => {
        setHasSearched(false);
        setIsSearching(false);
        setPublicationIds([]);
        setPublications([]);
        fetchedPublicationIdsRef.current = new Set();
        setError(null);
        setSearchQuery('');
        setStreamProgress(0);
        setStreamStatus(null);
        setBatchCount({ current: 0, total: 0 });
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
    };

    return (
        <div className="min-h-screen bg-background flex flex-col">
            <Header />

            <main className="flex-grow pt-[var(--header-height)]">
                {!hasSearched ? (
                    /* ===== INITIAL STATE: Google-style Centered Search ===== */
                    <div className="relative min-h-[calc(100vh-var(--header-height))] flex flex-col">


                        {/* Centered Search */}
                        <div className="flex-1 flex flex-col items-center justify-center px-4 -mt-20">
                            <div className="text-center mb-12 max-w-2xl">
                                <Sparkles className="w-16 h-16 mx-auto mb-6 text-purple-500" />
                                <h1 className="text-5xl font-bold text-[#1E1E1E] tracking-tight mb-4">
                                    Dataset Explorer
                                </h1>
                                <p className="text-lg text-gray-500 leading-relaxed">
                                    Use semantic search to find relevant papers across conference publications
                                </p>
                            </div>

                            {/* Large Centered Search Bar */}
                            <div className="w-full max-w-3xl">

                                <div className="relative bg-white rounded-full shadow-lg border border-gray-200 hover:shadow-xl transition-shadow">
                                    <Search className="absolute left-6 top-1/2 -translate-y-1/2 text-gray-400 w-6 h-6" />
                                    <input
                                        type="text"
                                        placeholder="Describe what you're looking for (e.g., 'transformer architectures for computer vision')..."
                                        className="w-full pl-16 pr-32 py-6 rounded-full text-lg border-0 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter' && searchQuery.trim()) {
                                                handleStreamingSearch();
                                            }
                                        }}
                                    />
                                    <Button
                                        onClick={handleStreamingSearch}
                                        disabled={!searchQuery.trim() || instancesLoading}
                                        size="lg"
                                        className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full px-8 bg-black hover:bg-gray-800"
                                    >
                                        Search
                                    </Button>
                                </div>

                                {/* Filters below search bar */}
                                <div className="mt-4 flex justify-start">
                                    <SearchFilters
                                        venues={venues}
                                        years={years}
                                        selectedVenue={selectedVenue}
                                        setSelectedVenue={setSelectedVenue}
                                        selectedYear={selectedYear}
                                        setSelectedYear={setSelectedYear}
                                        isLoading={instancesLoading}
                                        topk={topk}
                                        setTopk={setTopk}
                                    />
                                </div>



                                {error && (
                                    <div className="mt-4 bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg flex items-center gap-2">
                                        <AlertCircle className="w-5 h-5 flex-shrink-0" />
                                        <span>{error}</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                ) : (
                    /* ===== AFTER SEARCH: Compact Layout with Results ===== */
                    <div className="relative">


                        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
                            {/* Filters above search bar */}
                            <div className="mb-4 flex justify-start">
                                <SearchFilters
                                    venues={venues}
                                    years={years}
                                    selectedVenue={selectedVenue}
                                    setSelectedVenue={setSelectedVenue}
                                    selectedYear={selectedYear}
                                    setSelectedYear={setSelectedYear}
                                    isLoading={instancesLoading || isSearching}
                                    topk={topk}
                                    setTopk={setTopk}
                                />
                            </div>

                            {/* Compact Search Bar */}
                            <div className="flex items-center gap-4 mb-6">
                                <div className="flex-1 relative bg-white rounded-lg border border-gray-200 shadow-sm">
                                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
                                    <input
                                        type="text"
                                        className="w-full pl-10 pr-24 py-3 rounded-lg border-0 focus:outline-none focus:ring-2 focus:ring-purple-500"
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter' && !isSearching && searchQuery.trim()) {
                                                handleStreamingSearch();
                                            }
                                        }}
                                        disabled={isSearching}
                                        placeholder="Search query..."
                                    />
                                    <Button
                                        onClick={handleStreamingSearch}
                                        disabled={isSearching || !searchQuery.trim()}
                                        size="sm"
                                        className="absolute right-2 top-1/2 -translate-y-1/2 bg-black hover:bg-gray-800"
                                    >
                                        {isSearching && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                                        Search
                                    </Button>
                                </div>
                                <Button
                                    onClick={handleReset}
                                    variant="outline"
                                    size="sm"
                                    className="gap-2"
                                >
                                    <X className="w-4 h-4" />
                                    Reset
                                </Button>
                            </div>

                            {/* Progress Indicator */}
                            {isSearching && (
                                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm mb-6 animate-in fade-in slide-in-from-top-4 duration-300">
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
                                            {publications.length} results loaded so far...
                                        </p>
                                    </div>
                                </div>
                            )}

                            {/* Error Message */}
                            {error && (
                                <div className="bg-red-50 border border-red-100 text-red-700 p-4 rounded-lg flex items-center gap-2 mb-6">
                                    <AlertCircle className="w-5 h-5 flex-shrink-0" />
                                    {error}
                                </div>
                            )}

                            {/* Results Table */}
                            {publications.length > 0 && (
                                <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                                    <div className="mb-4 flex items-center justify-between">
                                        <h2 className="text-lg font-semibold text-gray-900">
                                            Search Results ({publications.length})
                                        </h2>
                                        {isFetchingPublications && (
                                            <span className="text-sm text-gray-500 flex items-center gap-2">
                                                <Loader2 className="w-4 h-4 animate-spin" />
                                                Loading details...
                                            </span>
                                        )}
                                    </div>
                                    <PublicationsTableEnhanced
                                        data={publications}
                                        pagination={{ count: publications.length, next: null, previous: null }}
                                        currentPage={1}
                                        onPageChange={() => { }}
                                        searchTerm=""
                                        onSearchChange={() => { }}
                                        sortField="rating"
                                        sortDirection="desc"
                                        onSortChange={() => { }}
                                        isFiltered={false}
                                        isLoading={isFetchingPublications}
                                    />
                                </div>
                            )}

                            {/* Empty State after search completes */}
                            {!isSearching && publications.length === 0 && publicationIds.length === 0 && !error && (
                                <div className="text-center py-20 text-gray-400">
                                    <Sparkles className="w-12 h-12 mx-auto mb-4 opacity-20" />
                                    <p className="text-lg">No results found. Try adjusting your query or filters.</p>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
