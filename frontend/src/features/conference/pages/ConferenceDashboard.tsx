import { useState, useMemo, memo } from 'react';
import { useDebounce } from '@/shared/hooks/useDebounce';
import { useVenues, useInstances, useDashboard, useOverview, usePublications } from '../hooks/useConference';
import { DashboardKPIs } from '../components/DashboardKPIs';
import { DashboardCharts } from '../components/DashboardCharts';
import PublicationsTable from '../components/PublicationsTable';
import { SessionList } from '../components/SessionList';
import ConferenceSelectionDrawer from '../components/ConferenceSelectionDrawer';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/shared/components/ui/tabs';
import { AlertCircle, Calendar, Filter, Sparkles, FileText, ChevronRight } from 'lucide-react';
import Header from '@/shared/components/layout/Header';
import { Button } from '@/shared/components/ui/button';
import ExportButton from '../components/ExportButton';
import { ImportToNotebookWizard } from '../components/ImportToNotebookWizard';
import { ImportResponse } from '../types';

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

  // Selection state for publications
  const [selectedPublicationIds, setSelectedPublicationIds] = useState<Set<string>>(new Set());
  const [showImportWizard, setShowImportWizard] = useState(false);

  const handleImportComplete = (response: ImportResponse) => {
    if (response.success) {
      setSelectedPublicationIds(new Set());
    }
  };

  const handleOpenImportWizard = () => {
    if (selectedPublicationIds.size === 0) {
      alert('Please select publications to import');
      return;
    }
    setShowImportWizard(true);
  };



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
    page_size: 50,
    search: debouncedPublicationSearch || undefined,
    aff_filter: selectedAffiliations.length > 0 ? selectedAffiliations.join(',') : undefined,
    ordering: getOrdering()
  } : undefined;

  const {
    data: publicationsData,
    isLoading: publicationsLoading,
    error: publicationsError
  } = usePublications(publicationsParams);

  // Get selected publications objects for export
  const selectedPublications = useMemo(() => {
    if (!publicationsData?.results) return [];
    return publicationsData.results.filter((p: any) => selectedPublicationIds.has(String(p.id)));
  }, [publicationsData, selectedPublicationIds]);

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
        {/* Modern Page Header - Refined Huawei Style */}
        <section className="bg-white border-b border-[#E3E3E3]">
          <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-10 relative">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-8">
              <div className="max-w-3xl">
                <div className="flex items-center gap-2 mb-6">
                  <span className="px-3 py-1 rounded bg-[#F5F5F5] text-xs font-medium text-[#666666] flex items-center gap-1 uppercase tracking-wide">
                    <Sparkles className="w-3 h-3 text-[#CE0E2D]" />
                    Analytics Dashboard
                  </span>
                </div>
                <h1 className="text-4xl md:text-[40px] font-extrabold text-[#000000] tracking-tight mb-4 leading-tight">
                  Conference Analytics
                </h1>
                <p className="text-lg text-[#666666] leading-relaxed max-w-2xl">
                  Explore academic trends, research impact, and publication insights across top-tier conferences.
                </p>
              </div>

              {/* Conference Selection Button */}
              <div>
                <button
                  onClick={() => setIsDrawerOpen(true)}
                  className="flex items-center space-x-3 px-8 py-4 rounded-lg bg-black text-white hover:opacity-80 transition-all duration-300 group shadow-[rgba(0,0,0,0.08)_0px_8px_12px]"
                >
                  <Filter className="w-4 h-4" />
                  <span className="font-medium text-[13px] tracking-wide uppercase">
                    {matchingInstance
                      ? `${matchingInstance.venue.name} ${matchingInstance.year}`
                      : 'Select Conference'}
                  </span>
                  <ChevronRight className="w-4 h-4 opacity-50 group-hover:translate-x-1 transition-transform" />
                </button>
              </div>
            </div>
          </div>
        </section>

        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="space-y-8">

            {/* Dashboard Content with Tabs */}
            {matchingInstance && (
              <div className="space-y-6">

                <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-[#E3E3E3] pb-0">
                    <TabsList className="bg-transparent p-0 border-none h-auto w-full sm:w-auto flex overflow-x-auto">
                      {['overview', 'sessions', 'publications'].map((tab) => (
                        <TabsTrigger
                          key={tab}
                          value={tab}
                          className="rounded-none border-b-2 border-transparent px-6 py-4 text-sm font-medium text-[#666666] hover:text-[#000000] data-[state=active]:border-[#CE0E2D] data-[state=active]:text-[#000000] data-[state=active]:bg-transparent transition-all capitalize tracking-wide shrink-0"
                        >
                          {tab}
                        </TabsTrigger>
                      ))}
                    </TabsList>

                    {/* Action Buttons - Only visible when Publications tab is active */}
                    {activeTab === 'publications' && (
                      <div className="flex items-center gap-3 py-3 sm:py-0">
                        {selectedPublicationIds.size > 0 && (
                          <span className="text-sm font-medium text-[#666666] bg-[#F5F5F5] px-3 py-1.5 rounded whitespace-nowrap">
                            {selectedPublicationIds.size} selected
                          </span>
                        )}

                        <Button
                          onClick={handleOpenImportWizard}
                          size="sm"
                          disabled={selectedPublicationIds.size === 0}
                          className="flex items-center gap-2 h-9 bg-[#CE0E2D] hover:bg-[#A20A22] text-white border-0 shadow-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed rounded-md px-4"
                        >
                          <Sparkles size={14} />
                          <span className="font-medium">DeepDive</span>
                        </Button>

                        <ExportButton
                          publications={publicationsData?.results || []}
                          selectedPublications={selectedPublications}
                          variant="outline"
                          size="sm"
                        />
                      </div>
                    )}
                  </div>

                  {/* Overview Tab */}
                  <TabsContent value="overview" className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    {(dashboardError || publicationsError) && (
                      <div className="bg-red-50 border border-red-100 rounded-lg p-6 flex items-start gap-4">
                        <AlertCircle className="h-6 w-6 text-[#CE0E2D] shrink-0" />
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
                    <PublicationsTable
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
                      showTitle={false}
                      pageSize={50}
                      externalSelectedIds={selectedPublicationIds}
                      onSelectionChange={setSelectedPublicationIds}
                    />
                  </TabsContent>
                </Tabs>
              </div>
            )}

            {/* No Selection State */}
            {!matchingInstance && !dashboardLoading && (
              <div className="flex flex-col items-center justify-center py-32 bg-white rounded-2xl border border-dashed border-[#E3E3E3]">
                <div className="w-20 h-20 bg-[#F5F5F5] rounded-full flex items-center justify-center mb-6">
                  <Calendar className="w-10 h-10 text-[#B1B1B1]" />
                </div>
                <h3 className="text-xl font-bold text-[#1E1E1E] mb-2">
                  Select a conference to explore
                </h3>
                <p className="text-[#666666] mb-8 text-center max-w-md">
                  Choose a venue and year to view detailed analytics, publications, and session information.
                </p>
                <button
                  onClick={() => setIsDrawerOpen(true)}
                  className="px-8 py-3 bg-black text-white rounded-lg font-medium text-sm hover:opacity-80 transition-all shadow-[rgba(0,0,0,0.08)_0px_8px_12px]"
                >
                  Select Conference
                </button>
              </div>
            )}
          </div>
        </div>
      </main>
      <ImportToNotebookWizard
        isOpen={showImportWizard}
        onClose={() => setShowImportWizard(false)}
        selectedPublicationIds={Array.from(selectedPublicationIds)}
        onImportComplete={handleImportComplete}
      />
    </div>
  );
}
