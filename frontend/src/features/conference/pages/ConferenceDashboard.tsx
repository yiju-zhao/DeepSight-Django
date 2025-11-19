import { useState, useMemo, memo } from 'react';
import { useDebounce } from '@/shared/hooks/useDebounce';
import { useVenues, useInstances, useDashboard, useOverview, usePublications } from '../hooks/useConference';
import { DashboardKPIs } from '../components/DashboardKPIs';
import { DashboardCharts } from '../components/DashboardCharts';
import PublicationsTableEnhanced from '../components/PublicationsTableEnhanced';
import { SessionTypeView } from '../components/SessionTypeView';
import ConferenceSelectionDrawer from '../components/ConferenceSelectionDrawer';
import { ImportStatusPanel } from '../components/ImportStatusPanel';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/shared/components/ui/tabs';
import { AlertCircle, Calendar, Filter } from 'lucide-react';
import AppLayout from '@/shared/components/layout/AppLayout';
import MainPageHeader from '@/shared/components/common/MainPageHeader';

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
    <AppLayout>
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

      <div className="flex flex-col min-h-screen bg-transparent">
        {/* Main Page Header with Conference Selection Button */}
        <MainPageHeader
          label="ANALYTICS"
          title="Conference Analytics"
          subtitle="Deep insights into academic conferences"
          icon={<Calendar className="w-6 h-6 text-[#CE0E2D]" />}
          rightActions={
            <div className="flex items-center space-x-3">
              {/* Conference Selection Button */}
              <button
                onClick={() => setIsDrawerOpen(true)}
                className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-white border border-[#E3E3E3] hover:border-black/30 hover:shadow-[rgba(0,0,0,0.08)_0px_8px_12px] transition-all duration-300"
              >
                <Filter className="w-4 h-4 text-[#1E1E1E]" />
                <span className="text-sm font-medium text-[#1E1E1E]">
                  {matchingInstance
                    ? `${matchingInstance.venue.name} ${matchingInstance.year}`
                    : 'Select Conference'}
                </span>
              </button>
            </div>
          }
        />

        <div className="flex-1 overflow-auto bg-white">
          <div className="max-w-7xl mx-auto px-4 md:px-10 lg:px-20 py-6 md:py-8">
            <div className="space-y-10 md:space-y-20">

          {/* Dashboard Content with Tabs */}
          {matchingInstance && (
            <div className="space-y-4">
              <div>
                <p className="text-[11px] uppercase tracking-[0.3px] text-[#7B7B7B]">
                  Selected conference
                </p>
                <div className="mt-1 flex flex-wrap items-baseline gap-2">
                  <h2 className="text-[24px] md:text-[28px] font-bold text-[#1E1E1E] leading-tight">
                    {matchingInstance.venue.name}
                  </h2>
                  <span className="text-sm md:text-base text-[#666666]">
                    {matchingInstance.year}
                  </span>
                </div>
              </div>

              <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                <TabsList className="w-full justify-start bg-[#F7F7F7] rounded-lg px-1 py-1 border border-[#E3E3E3]">
                  <TabsTrigger
                    value="overview"
                    className="rounded-md text-sm data-[state=active]:bg-white data-[state=active]:shadow-[rgba(0,0,0,0.08)_0px_6px_10px] data-[state=active]:border-transparent"
                  >
                    Overview
                  </TabsTrigger>
                  <TabsTrigger
                    value="sessions"
                    className="rounded-md text-sm data-[state=active]:bg-white data-[state=active]:shadow-[rgba(0,0,0,0.08)_0px_6px_10px] data-[state=active]:border-transparent"
                  >
                    Sessions
                  </TabsTrigger>
                  <TabsTrigger
                    value="publications"
                    className="rounded-md text-sm data-[state=active]:bg-white data-[state=active]:shadow-[rgba(0,0,0,0.08)_0px_6px_10px] data-[state=active]:border-transparent"
                  >
                    Publications
                  </TabsTrigger>
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
                  <Calendar className="w-16 h-16 text-[#666666] mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-[#1E1E1E] mb-2">
                    Select a conference to explore
                  </h3>
                  <p className="text-[#666666] mb-6">
                    Click "Select Conference" to view analytics and publications
                  </p>
                  <button
                    onClick={() => setIsDrawerOpen(true)}
                    className="px-6 py-3 bg-black text-white rounded-lg hover:opacity-80 transition-opacity duration-300"
                  >
                    Select Conference
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Import Status Panel */}
      <ImportStatusPanel />
    </AppLayout>
  );
}
