import { useState, useMemo, useEffect, useRef } from 'react';
import { useVenues, useInstances, useDashboard, useOverview, usePublications } from '../hooks/useConference';
import { DashboardKPIs } from '../components/DashboardKPIs';
import { DashboardCharts } from '../components/DashboardCharts';
import { PublicationsTable } from '../components/PublicationsTable';
import { AlertCircle, TrendingUp, Search, Calendar, MapPin, Star, Users, FileText } from 'lucide-react';
import AppLayout from '@/shared/components/layout/AppLayout';
import MainPageHeader from '@/shared/components/common/MainPageHeader';

export default function ConferenceDashboard() {
  const [selectedVenue, setSelectedVenue] = useState<string>('');
  const [selectedYear, setSelectedYear] = useState<number | undefined>();
  const [selectedInstance, setSelectedInstance] = useState<number | undefined>();
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');

  // Ref for the dashboard content section
  const dashboardContentRef = useRef<HTMLDivElement>(null);

  // Fetch all instances first to build dropdown options
  const { data: instances, isLoading: instancesLoading } = useInstances();

  // Process and group instances for better UI
  const { groupedConferences, filteredInstances, popularConferences } = useMemo(() => {
    if (!instances) return { groupedConferences: {}, filteredInstances: [], popularConferences: [] };

    // Filter instances based on search term
    const filtered = instances.filter(instance =>
      instance.venue.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      instance.year.toString().includes(searchTerm)
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

    // Sort by most recent and popular (mock popularity for now)
    const popular = filtered
      .sort((a, b) => b.year - a.year)
      .slice(0, 6);

    return {
      groupedConferences: grouped,
      filteredInstances: filtered,
      popularConferences: popular
    };
  }, [instances, searchTerm]);

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

  // Fetch publications separately with pagination
  const publicationsParams = matchingInstance ? {
    instance: matchingInstance.instance_id,
    page: currentPage,
    page_size: 20
  } : undefined;

  const {
    data: publicationsData,
    isLoading: publicationsLoading,
    error: publicationsError
  } = usePublications(publicationsParams);

  // Fetch overview data
  const { data: overviewData } = useOverview();

  // Auto-scroll to dashboard content when a conference is selected
  useEffect(() => {
    if (matchingInstance && dashboardContentRef.current) {
      // Small delay to ensure the content is rendered
      const timer = setTimeout(() => {
        dashboardContentRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }, 300);

      return () => clearTimeout(timer);
    }
  }, [matchingInstance]);

  const handleVenueChange = (venue: string) => {
    setSelectedVenue(venue);
    setSelectedYear(undefined);
    setSelectedInstance(undefined);
    setCurrentPage(1);
  };

  const handleYearChange = (year: number | undefined) => {
    setSelectedYear(year);
    setSelectedInstance(undefined);
    setCurrentPage(1);
  };

  const handleInstanceSelect = (instanceId: number) => {
    const instance = instances?.find(i => i.instance_id === instanceId);
    if (instance) {
      setSelectedVenue(instance.venue.name);
      setSelectedYear(instance.year);
      setSelectedInstance(instanceId);
      setCurrentPage(1);
    }
  };

  return (
    <AppLayout>
      <div className="flex flex-col min-h-screen bg-gray-50">
        <MainPageHeader
          title="Conference Analysis"
          subtitle="Explore detailed statistics, charts, and publication lists for specific conferences and years"
          icon={<TrendingUp className="w-5 h-5 text-white" />}
          iconColor="from-purple-500 to-purple-600"
        />

        <div className="flex-1 p-8 overflow-auto">
          <div className="max-w-7xl mx-auto">
            <div className="space-y-8">

          {/* Enhanced Conference Selection */}
          <div className="space-y-6">
            {/* Search Header */}
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl shadow-lg p-6 text-white">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-2xl font-bold">Explore Conferences</h2>
                  <p className="text-blue-100 mt-1">Discover insights from leading academic venues</p>
                </div>
                {selectedVenue && selectedYear && (
                  <div className="bg-white bg-opacity-20 px-4 py-2 rounded-lg backdrop-blur-sm">
                    <div className="text-sm font-medium">{selectedVenue} {selectedYear}</div>
                  </div>
                )}
              </div>

              {/* Search Bar */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type="text"
                  placeholder="Search conferences, venues, or years..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-white bg-opacity-20 backdrop-blur-sm border border-white border-opacity-30 rounded-lg text-white placeholder-blue-200 focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-50"
                />
              </div>
            </div>

            {/* Popular Conferences */}
            {!searchTerm && popularConferences.length > 0 && (
              <div className="bg-white rounded-xl shadow-sm border p-6">
                <div className="flex items-center mb-4">
                  <Star className="w-5 h-5 text-yellow-500 mr-2" />
                  <h3 className="text-lg font-semibold text-gray-900">Recent & Popular</h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {popularConferences.map((instance) => (
                    <button
                      key={instance.instance_id}
                      onClick={() => handleInstanceSelect(instance.instance_id)}
                      className={`group relative p-4 rounded-lg border-2 transition-all duration-200 text-left ${
                        matchingInstance?.instance_id === instance.instance_id
                          ? 'border-blue-500 bg-blue-50 shadow-md'
                          : 'border-gray-200 hover:border-blue-300 hover:shadow-sm'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
                          {instance.venue.name}
                        </div>
                        <div className="flex items-center text-sm text-gray-500">
                          <Calendar className="w-4 h-4 mr-1" />
                          {instance.year}
                        </div>
                      </div>
                      <div className="text-sm text-gray-600 mb-2">{instance.venue.type}</div>
                      {instance.location && (
                        <div className="flex items-center text-xs text-gray-500">
                          <MapPin className="w-3 h-3 mr-1" />
                          {instance.location}
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* All Conferences Grid */}
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center">
                  <Users className="w-5 h-5 text-blue-500 mr-2" />
                  <h3 className="text-lg font-semibold text-gray-900">All Conferences</h3>
                  <span className="ml-2 text-sm text-gray-500">
                    ({Object.keys(groupedConferences).length} venues)
                  </span>
                </div>
              </div>

              {instancesLoading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {[...Array(6)].map((_, i) => (
                    <div key={i} className="animate-pulse">
                      <div className="h-32 bg-gray-200 rounded-lg"></div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {Object.entries(groupedConferences).map(([venueName, venueData]) => (
                    <div
                      key={venueName}
                      className="group bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl p-6 border border-gray-200 hover:shadow-lg transition-all duration-300"
                    >
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h4 className="font-bold text-lg text-gray-900 group-hover:text-blue-600 transition-colors">
                            {venueName}
                          </h4>
                          <p className="text-sm text-gray-600 mt-1">{venueData.venue.type}</p>
                        </div>
                        <FileText className="w-5 h-5 text-gray-400 group-hover:text-blue-500 transition-colors" />
                      </div>

                      <div className="mb-4">
                        <div className="flex items-center text-sm text-gray-600 mb-2">
                          <Calendar className="w-4 h-4 mr-2" />
                          {venueData.yearRange.min === venueData.yearRange.max
                            ? venueData.yearRange.min
                            : `${venueData.yearRange.min} - ${venueData.yearRange.max}`}
                        </div>
                        <div className="text-sm text-gray-600">
                          {venueData.instances.length} instance{venueData.instances.length !== 1 ? 's' : ''} available
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {venueData.instances
                          .sort((a: any, b: any) => b.year - a.year)
                          .map((instance: any) => (
                          <button
                            key={instance.instance_id}
                            onClick={() => handleInstanceSelect(instance.instance_id)}
                            className={`px-3 py-1 text-xs rounded-full transition-all duration-200 ${
                              matchingInstance?.instance_id === instance.instance_id
                                ? 'bg-blue-600 text-white shadow-md'
                                : 'bg-white text-gray-700 border border-gray-300 hover:bg-blue-50 hover:border-blue-300'
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
                  <Search className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No conferences found</h3>
                  <p className="text-gray-500">Try adjusting your search terms</p>
                </div>
              )}
            </div>
          </div>

          {/* Dashboard Content */}
          {(dashboardError || publicationsError) && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center">
                <AlertCircle className="h-5 w-5 text-red-400 mr-2" />
                <div className="text-red-800">
                  <div className="font-medium">Error loading dashboard data</div>
                  <div className="text-sm mt-1">
                    {dashboardError?.message || publicationsError?.message || 'Please check your selection and try again.'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {matchingInstance && (
            <div ref={dashboardContentRef} className="space-y-8">
              {/* KPIs */}
              {dashboardData && (
                <DashboardKPIs data={dashboardData.kpis} isLoading={dashboardLoading} />
              )}

              {/* Charts */}
              {dashboardData && (
                <DashboardCharts data={dashboardData.charts} isLoading={dashboardLoading} />
              )}

              {/* Publications Table */}
              <PublicationsTable
                data={publicationsData?.results || []}
                pagination={{
                  count: publicationsData?.count || 0,
                  next: publicationsData?.next || null,
                  previous: publicationsData?.previous || null
                }}
                currentPage={currentPage}
                onPageChange={setCurrentPage}
                isLoading={publicationsLoading}
              />
            </div>
          )}

          {/* No Selection State */}
          {!matchingInstance && !dashboardLoading && (
            <div className="text-center py-16">
              <h3 className="text-lg font-medium text-gray-500 mb-2">
                Select a conference and year to view dashboard
              </h3>
              <p className="text-gray-400">
                Choose from the dropdowns above to explore publication data and analytics
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
