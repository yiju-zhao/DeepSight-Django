import { useState, useMemo, useEffect, useRef, memo } from 'react';
import { useDebounce } from '@/shared/hooks/useDebounce';
import { useVenues, useInstances, useDashboard, useOverview, usePublications } from '../hooks/useConference';
import { DashboardKPIs } from '../components/DashboardKPIs';
import { DashboardCharts } from '../components/DashboardCharts';
import PublicationsTableEnhanced from '../components/PublicationsTableEnhanced';
import { SessionTypeView } from '../components/SessionTypeView';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/shared/components/ui/tabs';
import { AlertCircle, TrendingUp, Search, Calendar as CalendarIcon, MapPin, Star, Users, FileText, ChevronDown, ChevronUp } from 'lucide-react';
import AppLayout from '@/shared/components/layout/AppLayout';

// Memoized dashboard content component to prevent unnecessary re-renders
const DashboardContent = memo(({
  dashboardData,
  dashboardLoading,
  ratingHistogramData,
  ratingHistogramLoading,
  publicationsData,
  publicationsLoading,
  currentPage,
  onPageChange,
  publicationSearchInput,
  onPublicationSearchChange,
  sortField,
  sortDirection,
  onSortChange,
  debouncedPublicationSearch,
  onBinSizeChange,
  currentBinSize
}: {
  dashboardData: any;
  dashboardLoading: boolean;
  ratingHistogramData: any;
  ratingHistogramLoading: boolean;
  publicationsData: any;
  publicationsLoading: boolean;
  currentPage: number;
  onPageChange: (page: number) => void;
  publicationSearchInput: string;
  onPublicationSearchChange: (search: string) => void;
  sortField: 'rating' | 'title';
  sortDirection: 'asc' | 'desc';
  onSortChange: (field: 'rating' | 'title', direction: 'asc' | 'desc') => void;
  debouncedPublicationSearch: string;
  onBinSizeChange: (binSize: number) => void;
  currentBinSize: number;
}) => (
  <div className="space-y-8">
    {/* KPIs */}
    {dashboardData && (
      <DashboardKPIs data={dashboardData.kpis} isLoading={dashboardLoading} />
    )}

    {/* Charts */}
    {dashboardData && (
      <DashboardCharts
        data={dashboardData.charts}
        isLoading={dashboardLoading}
        ratingHistogramData={ratingHistogramData?.charts?.ratings_histogram_fine}
        ratingHistogramLoading={ratingHistogramLoading}
        onBinSizeChange={onBinSizeChange}
        currentBinSize={currentBinSize}
      />
    )}
  </div>
));

DashboardContent.displayName = 'DashboardContent';

export default function ConferenceDashboard() {
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedVenue, setSelectedVenue] = useState<string>('');
  const [selectedYear, setSelectedYear] = useState<number | undefined>();
  const [selectedInstance, setSelectedInstance] = useState<number | undefined>();
  const [currentPage, setCurrentPage] = useState(1);
  const [allConferencesExpanded, setAllConferencesExpanded] = useState(false); // Collapsed by default
  // Separate search states to avoid coupling
  const [conferenceSearchInput, setConferenceSearchInput] = useState(''); // For conference list search
  const [publicationSearchInput, setPublicationSearchInput] = useState(''); // For publications search
  const [selectedAffiliations, setSelectedAffiliations] = useState<string[]>([]); // For affiliation filter
  const [sortField, setSortField] = useState<'rating' | 'title'>('rating');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [binSize, setBinSize] = useState(0.5); // Default bin size for rating histogram

  // Debounce search input to avoid too many API calls
  const debouncedPublicationSearch = useDebounce(publicationSearchInput, 500); // 500ms delay (publications only)

  // Ref for the dashboard content section
  const dashboardContentRef = useRef<HTMLDivElement>(null);

  // Fetch all instances first to build dropdown options
  const { data: instances, isLoading: instancesLoading } = useInstances();

  // Process and group instances for better UI
  const { groupedConferences, popularConferences } = useMemo(() => {
    if (!instances) return { groupedConferences: {}, popularConferences: [] };

    // Filter instances based on search term
    const filtered = instances.filter(instance =>
      instance.venue.name.toLowerCase().includes(conferenceSearchInput.toLowerCase()) ||
      instance.year.toString().includes(conferenceSearchInput)
    );

    // Group by venue
    const grouped = filtered.reduce((acc, instance) => {
      const venue = instance.venue.name;
      if (!acc[venue]) {
        acc[venue] = {
          venue: instance.venue,
          instances: [],
          totalPapers: 0,
          yearRange: { min: instance.year, max: instance.year }
        };
      }
      acc[venue].instances.push(instance);
      acc[venue].yearRange.min = Math.min(acc[venue].yearRange.min, instance.year);
      acc[venue].yearRange.max = Math.max(acc[venue].yearRange.max, instance.year);
      return acc;
    }, {} as Record<string, any>);

    // Sort by most recent start date and take only 3
    const popular = filtered
      .sort((a, b) => new Date(b.start_date).getTime() - new Date(a.start_date).getTime())
      .slice(0, 3);

    return {
      groupedConferences: grouped,
      popularConferences: popular
    };
  }, [instances, conferenceSearchInput]);

  // Find the matching instance for selected venue+year combo
  const matchingInstance = instances?.find(
    i => i.venue.name === selectedVenue && i.year === selectedYear
  );

  // Fetch dashboard data (KPIs and charts) only when we have a matching instance
  const dashboardParams = matchingInstance ? {
    instance: matchingInstance.instance_id
  } : {};

  const {
    data: dashboardData,
    isLoading: dashboardLoading,
    error: dashboardError
  } = useDashboard(dashboardParams);

  // Separate API call for rating histogram with bin size
  const ratingHistogramParams = matchingInstance ? {
    instance: matchingInstance.instance_id,
    bin_size: binSize
  } : {};

  const {
    data: ratingHistogramData,
    isLoading: ratingHistogramLoading,
  } = useDashboard(ratingHistogramParams);


  // Convert sort parameters to Django ordering format
  const getOrdering = () => {
    const prefix = sortDirection === 'desc' ? '-' : '';
    return `${prefix}${sortField}`;
  };

  // Fetch publications separately with pagination
  const publicationsParams = matchingInstance ? {
    instance: matchingInstance.instance_id,
    page: currentPage,
    page_size: 20,
    search: debouncedPublicationSearch || undefined,
    aff_filter: selectedAffiliations.length > 0 ? selectedAffiliations.join(',') : undefined,
    ordering: getOrdering()
  } : undefined;

  const {
    data: publicationsData,
    isLoading: publicationsLoading,
    error: publicationsError
  } = usePublications(publicationsParams);

  // Overview data hook available but not used in this component
  // const { data: overviewData } = useOverview();

  // Auto-scroll to dashboard content when a conference is selected
  const scrollToDashboard = () => {
    if (dashboardContentRef.current) {
      // Small delay to ensure the content is rendered
      setTimeout(() => {
        dashboardContentRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }, 300);
    }
  };

  // Auto-scroll when matchingInstance changes (new selection)
  useEffect(() => {
    if (matchingInstance) {
      scrollToDashboard();
    }
  }, [matchingInstance]);

  const handleVenueChange = (venue: string) => {
    setSelectedVenue(venue);
    setSelectedYear(undefined);
    setSelectedInstance(undefined);
    setCurrentPage(1);
    setPublicationSearchInput(''); // Reset publications search when changing venue
    setSelectedAffiliations([]); // Reset affiliation filter when changing venue
  };

  const handleYearChange = (year: number | undefined) => {
    setSelectedYear(year);
    setSelectedInstance(undefined);
    setCurrentPage(1);
    setPublicationSearchInput(''); // Reset publications search when changing year
    setSelectedAffiliations([]); // Reset affiliation filter when changing year
  };

  const handleInstanceSelect = (instanceId: number) => {
    const instance = instances?.find(i => i.instance_id === instanceId);
    if (instance) {
      setSelectedVenue(instance.venue.name);
      setSelectedYear(instance.year);
      setSelectedInstance(instanceId);
      setCurrentPage(1);
      setPublicationSearchInput(''); // Reset publications search when changing instance
      setSelectedAffiliations([]); // Reset affiliation filter when changing instance

      // Always scroll to dashboard when an instance is clicked, even if it's already selected
      setTimeout(() => scrollToDashboard(), 100);
    }
  };

  const handlePublicationSearchChange = useMemo(() =>
    (search: string) => {
      setPublicationSearchInput(search); // Update publications search
      setCurrentPage(1); // Reset to first page when searching
    }, []
  );

  const handleSortChange = useMemo(() =>
    (field: 'rating' | 'title', direction: 'asc' | 'desc') => {
      setSortField(field);
      setSortDirection(direction);
      setCurrentPage(1); // Reset to first page when sorting changes
    }, []
  );

  const handlePageChange = useMemo(() =>
    (page: number) => setCurrentPage(page),
    []
  );


  return (
    <AppLayout>
      <div className="flex flex-col min-h-screen bg-white">
        <div className="flex-1 p-6 overflow-auto">
          <div className="max-w-7xl mx-auto">
            <div className="space-y-6">

          {/* HUAWEI Style Header */}
          <div className="space-y-4">
            {/* Black Header with Title */}
            <div className="bg-black rounded-lg shadow-[rgba(0,0,0,0.08)_0px_8px_12px] p-4 text-white">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-2xl font-bold">Conference Dashboard</h2>
                  <p className="text-white/70 mt-1">Explore academic conference data and insights</p>
                </div>
                {selectedVenue && selectedYear && (
                  <div className="bg-white/10 px-4 py-2 rounded-md backdrop-blur-sm border border-white/20">
                    <div className="text-sm font-medium">{selectedVenue} {selectedYear}</div>
                  </div>
                )}
              </div>

          {/* Search Bar - HUAWEI Style */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/50 w-5 h-5" />
            <input
              type="text"
              placeholder="Search conferences, venues, or years..."
              value={conferenceSearchInput}
              onChange={(e) => setConferenceSearchInput(e.target.value)}
              className="w-full pl-10 pr-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-md text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/30 transition-all duration-300"
            />
          </div>
        </div>

        {/* Recent Conferences - Horizontal Scroll */}
        {!conferenceSearchInput && popularConferences.length > 0 && (
          <div className="bg-white rounded-lg shadow-[rgba(0,0,0,0.08)_0px_8px_12px] border border-[#E3E3E3] p-4">
            <div className="flex items-center mb-3">
              <Star className="w-5 h-5 text-[#CE0E2D] mr-2" />
              <h3 className="text-base font-semibold text-[#1E1E1E]">Recent</h3>
            </div>
            <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-[#E3E3E3] scrollbar-track-transparent">
              {popularConferences.map((instance) => (
                <button
                  key={instance.instance_id}
                  onClick={() => handleInstanceSelect(instance.instance_id)}
                  className={`group relative flex-shrink-0 w-72 p-3 rounded-lg border transition-all duration-300 text-left shadow-[rgba(0,0,0,0.01)_0px_3px_6px] hover:shadow-[rgba(0,0,0,0.08)_0px_8px_12px] ${
                    matchingInstance?.instance_id === instance.instance_id
                      ? 'border-black bg-black/5'
                      : 'border-[#E3E3E3] hover:border-black/30'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="font-semibold text-[#1E1E1E] text-sm transition-colors truncate">
                      {instance.venue.name}
                    </div>
                    <div className="flex items-center text-xs text-[#666666] ml-2">
                      <CalendarIcon className="w-3.5 h-3.5 mr-1" />
                      {instance.year}
                    </div>
                  </div>
                  <div className="text-xs text-[#666666] mb-1.5">{instance.venue.type}</div>
                  {instance.location && (
                    <div className="flex items-center text-xs text-[#666666]">
                      <MapPin className="w-3 h-3 mr-1" />
                      <span className="truncate">{instance.location}</span>
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

            {/* All Conferences Grid - Collapsible */}
            <div className="bg-white rounded-lg shadow-[rgba(0,0,0,0.08)_0px_8px_12px] border border-[#E3E3E3] p-4">
              <button
                onClick={() => setAllConferencesExpanded(!allConferencesExpanded)}
                className="flex items-center justify-between w-full mb-4 hover:opacity-80 transition-opacity duration-300"
              >
                <div className="flex items-center">
                  <Users className="w-5 h-5 text-[#1E1E1E] mr-2 opacity-80" />
                  <h3 className="text-base font-semibold text-[#1E1E1E]">All Conferences</h3>
                  <span className="ml-2 text-sm text-[#666666]">
                    ({Object.keys(groupedConferences).length} venues)
                  </span>
                </div>
                {allConferencesExpanded ? (
                  <ChevronUp className="w-5 h-5 text-[#666666]" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-[#666666]" />
                )}
              </button>

              {allConferencesExpanded && (
                <>
                  {instancesLoading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {[...Array(6)].map((_, i) => (
                        <div key={i} className="animate-pulse">
                          <div className="h-32 bg-[#F5F5F5] rounded-lg"></div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {Object.entries(groupedConferences).map(([venueName, venueData]) => (
                        <div
                          key={venueName}
                          className="group bg-white rounded-lg p-4 border border-[#E3E3E3] hover:shadow-[rgba(0,0,0,0.12)_0px_12px_20px] transition-all duration-300"
                        >
                          <div className="flex items-start justify-between mb-3">
                            <div>
                              <h4 className="font-bold text-base text-[#1E1E1E] transition-colors">
                                {venueName}
                              </h4>
                            </div>
                            <FileText className="w-4 h-4 text-[#666666] opacity-60 transition-opacity" />
                          </div>

                          <div className="flex flex-wrap gap-2">
                            {venueData.instances
                              .sort((a: any, b: any) => new Date(b.start_date).getTime() - new Date(a.start_date).getTime())
                              .map((instance: any) => (
                              <button
                                key={instance.instance_id}
                                onClick={() => handleInstanceSelect(instance.instance_id)}
                                className={`px-2.5 py-1 text-xs rounded-md transition-all duration-300 ${
                                  matchingInstance?.instance_id === instance.instance_id
                                    ? 'bg-black text-white'
                                    : 'bg-white text-[#1E1E1E] border border-[#E3E3E3] hover:border-black/30'
                                }`}
                              >
                                {instance.year}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {!instancesLoading && Object.keys(groupedConferences).length === 0 && (
                    <div className="text-center py-12">
                      <Search className="w-12 h-12 text-[#666666] mx-auto mb-4" />
                      <h3 className="text-base font-medium text-[#1E1E1E] mb-2">No conferences found</h3>
                      <p className="text-sm text-[#666666]">Try adjusting your search terms</p>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Dashboard Content with Tabs */}
          {matchingInstance && (
            <div ref={dashboardContentRef}>
              <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                <TabsList className="w-full justify-start">
                  <TabsTrigger value="overview">Overview</TabsTrigger>
                  <TabsTrigger value="sessions">Sessions</TabsTrigger>
                  <TabsTrigger value="publications">Publications</TabsTrigger>
                </TabsList>

                {/* Overview Tab */}
                <TabsContent value="overview" className="space-y-6">
                  {(dashboardError || publicationsError) && (
                    <div className="bg-[#CE0E2D]/10 border border-[#CE0E2D]/20 rounded-lg p-4">
                      <div className="flex items-center">
                        <AlertCircle className="h-5 w-5 text-[#CE0E2D] mr-2" />
                        <div className="text-[#1E1E1E]">
                          <div className="font-medium">Error loading dashboard data</div>
                          <div className="text-sm mt-1 text-[#666666]">
                            {dashboardError?.message || publicationsError?.message || 'Please check your selection and try again.'}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  <DashboardContent
                    dashboardData={dashboardData}
                    dashboardLoading={dashboardLoading}
                    ratingHistogramData={ratingHistogramData}
                    ratingHistogramLoading={ratingHistogramLoading}
                    publicationsData={publicationsData}
                    publicationsLoading={publicationsLoading}
                    currentPage={currentPage}
                    onPageChange={handlePageChange}
                    publicationSearchInput={publicationSearchInput}
                    onPublicationSearchChange={handlePublicationSearchChange}
                    sortField={sortField}
                    sortDirection={sortDirection}
                    onSortChange={handleSortChange}
                    debouncedPublicationSearch={debouncedPublicationSearch}
                    onBinSizeChange={setBinSize}
                    currentBinSize={binSize}
                  />
                </TabsContent>

                {/* Sessions Tab */}
                <TabsContent value="sessions">
                  <SessionTypeView instanceId={matchingInstance.instance_id} />
                </TabsContent>

                {/* Publications Tab */}
                <TabsContent value="publications">
                  <PublicationsTableEnhanced
                    data={publicationsData?.results || []}
                    pagination={{
                      count: publicationsData?.count || 0,
                      next: publicationsData?.next || null,
                      previous: publicationsData?.previous || null
                    }}
                    currentPage={currentPage}
                    onPageChange={handlePageChange}
                    searchTerm={publicationSearchInput}
                    onSearchChange={handlePublicationSearchChange}
                    selectedAffiliations={selectedAffiliations}
                    onAffiliationFilterChange={setSelectedAffiliations}
                    sortField={sortField}
                    sortDirection={sortDirection}
                    onSortChange={handleSortChange}
                    isFiltered={!!debouncedPublicationSearch || selectedAffiliations.length > 0}
                    isLoading={publicationsLoading}
                    onViewDetails={(publication) => {
                      console.log('View details for:', publication.title);
                    }}
                  />
                </TabsContent>
              </Tabs>
            </div>
          )}

          {/* No Selection State */}
          {!matchingInstance && !dashboardLoading && (
            <div className="text-center py-16 bg-white rounded-lg shadow-[rgba(0,0,0,0.08)_0px_8px_12px] border border-[#E3E3E3]">
              <h3 className="text-lg font-medium text-[#1E1E1E] mb-2">
                Select a conference to explore
              </h3>
              <p className="text-[#666666]">
                Choose a conference from above to view analytics and publications
              </p>
            </div>
          )}
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
