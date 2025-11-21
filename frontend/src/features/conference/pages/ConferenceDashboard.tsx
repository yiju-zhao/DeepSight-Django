import { useState, useMemo, memo } from 'react';
import { useDebounce } from '@/shared/hooks/useDebounce';
import { useVenues, useInstances, useDashboard, useOverview, usePublications } from '../hooks/useConference';
import { DashboardKPIs } from '../components/DashboardKPIs';
import { DashboardCharts } from '../components/DashboardCharts';
import PublicationsTableEnhanced from '../components/PublicationsTableEnhanced';
import { SessionList } from '../components/SessionList';
import ConferenceSelectionDrawer from '../components/ConferenceSelectionDrawer';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/shared/components/ui/tabs';
import { AlertCircle, Calendar, Filter, Sparkles } from 'lucide-react';
import Header from '@/shared/components/layout/Header';

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
  const [isDrawerOpen, setIsDrawerOpen] = useState(false); // Drawer state
  // Separate search states to avoid coupling
  const [conferenceSearchInput, setConferenceSearchInput] = useState(''); // For conference list search
  const [publicationSearchInput, setPublicationSearchInput] = useState(''); // For publications search
  const [selectedAffiliations, setSelectedAffiliations] = useState<string[]>([]); // For affiliation filter
  const [sortField, setSortField] = useState<'rating' | 'title'>('rating');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [binSize, setBinSize] = useState(0.5); // Default bin size for rating histogram

  // Debounce search input to avoid too many API calls
  const debouncedPublicationSearch = useDebounce(publicationSearchInput, 500); // 500ms delay (publications only)

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
    <div className="min-h-screen bg-background flex flex-col">
      <Header />

      {/* Conference Selection Drawer */}
      <ConferenceSelectionDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        conferenceSearchInput={conferenceSearchInput}
        onSearchInputChange={setConferenceSearchInput}
        popularConferences={popularConferences}
        groupedConferences={groupedConferences}
        selectedInstance={matchingInstance}
        onInstanceSelect={handleInstanceSelect}
        instancesLoading={instancesLoading}
        allConferencesExpanded={allConferencesExpanded}
        onToggleAllConferences={() => setAllConferencesExpanded(!allConferencesExpanded)}
      />

      <main className="flex-grow pt-[var(--header-height)]">
        {/* Modern Page Header */}
        <section className="relative bg-white border-b border-gray-100">
          <div className="absolute inset-0 bg-gradient-to-b from-gray-50/50 to-white/20 pointer-events-none" />
          <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-12 relative z-10">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
              <div className="max-w-3xl">
                <div className="flex items-center gap-2 mb-4">
                  <span className="px-3 py-1 rounded-full bg-blue-50 text-xs font-medium text-blue-600 flex items-center gap-1">
                    <Sparkles className="w-3 h-3" />
                    Analytics
                  </span>
                </div>
                <h1 className="text-4xl font-bold text-[#1E1E1E] tracking-tight mb-4">
                  Conference Analytics
                </h1>
                <p className="text-lg text-gray-500 leading-relaxed">
                  Deep insights into academic conferences, publications, and trends.
                </p>
              </div>

              {/* Conference Selection Button */}
              <button
                onClick={() => setIsDrawerOpen(true)}
                className="flex items-center space-x-2 px-6 py-3 rounded-full bg-black text-white hover:bg-gray-800 hover:shadow-lg transition-all duration-300 group"
              >
                <Filter className="w-4 h-4 group-hover:scale-110 transition-transform" />
                <span className="font-medium">
                  {matchingInstance
                    ? `${matchingInstance.venue.name} ${matchingInstance.year}`
                    : 'Select Conference'}
                </span>
              </button>
            </div>
          </div>
        </section>

        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="space-y-10">

            {/* Dashboard Content with Tabs */}
            {matchingInstance && (
              <div className="space-y-8">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.3px] text-[#7B7B7B] mb-2">
                    Selected conference
                  </p>
                  <div className="flex flex-wrap items-baseline gap-3">
                    <h2 className="text-3xl font-bold text-[#1E1E1E] leading-tight">
                      {matchingInstance.venue.name}
                    </h2>
                    <span className="text-xl text-[#666666]">
                      {matchingInstance.year}
                    </span>
                  </div>
                </div>

                <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-8">
                  <TabsList className="w-full justify-start bg-transparent p-0 border-b border-gray-200 rounded-none h-auto">
                    {['overview', 'sessions', 'publications'].map((tab) => (
                      <TabsTrigger
                        key={tab}
                        value={tab}
                        className="rounded-none border-b-2 border-transparent px-6 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 data-[state=active]:border-black data-[state=active]:text-black data-[state=active]:bg-transparent transition-all capitalize"
                      >
                        {tab}
                      </TabsTrigger>
                    ))}
                  </TabsList>

                  {/* Overview Tab */}
                  <TabsContent value="overview" className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    {(dashboardError || publicationsError) && (
                      <div className="bg-red-50 border border-red-100 rounded-xl p-6 flex items-start gap-4">
                        <AlertCircle className="h-6 w-6 text-red-600 shrink-0" />
                        <div>
                          <h4 className="font-medium text-red-900">Error loading dashboard data</h4>
                          <p className="text-sm mt-1 text-red-700">
                            {dashboardError?.message || publicationsError?.message || 'Please check your selection and try again.'}
                          </p>
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
                  <TabsContent value="sessions" className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <SessionList instanceId={matchingInstance.instance_id} />
                  </TabsContent>

                  {/* Publications Tab */}
                  <TabsContent value="publications" className="animate-in fade-in slide-in-from-bottom-4 duration-500">
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
                    />
                  </TabsContent>
                </Tabs>
              </div>
            )}

            {/* No Selection State */}
            {!matchingInstance && !dashboardLoading && (
              <div className="flex flex-col items-center justify-center py-24 bg-white rounded-2xl border border-dashed border-gray-200">
                <div className="w-20 h-20 bg-gray-50 rounded-full flex items-center justify-center mb-6">
                  <Calendar className="w-10 h-10 text-gray-400" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  Select a conference to explore
                </h3>
                <p className="text-gray-500 mb-8 text-center max-w-md">
                  Choose a venue and year to view detailed analytics, publications, and session information.
                </p>
                <button
                  onClick={() => setIsDrawerOpen(true)}
                  className="px-8 py-3 bg-black text-white rounded-full font-medium hover:bg-gray-800 transition-colors shadow-lg hover:shadow-xl"
                >
                  Select Conference
                </button>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
