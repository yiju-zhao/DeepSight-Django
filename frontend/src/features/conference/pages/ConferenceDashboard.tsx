import { useState } from 'react';
import { useVenues, useInstances, useDashboard, useOverview } from '../hooks/useConference';
import { DashboardKPIs } from '../components/DashboardKPIs';
import { DashboardCharts } from '../components/DashboardCharts';
import { PublicationsTable } from '../components/PublicationsTable';
import { AlertCircle } from 'lucide-react';

export default function ConferenceDashboard() {
  const [selectedVenue, setSelectedVenue] = useState<string>('');
  const [selectedYear, setSelectedYear] = useState<number | undefined>();
  const [selectedInstance, setSelectedInstance] = useState<number | undefined>();
  const [currentPage, setCurrentPage] = useState(1);

  // Fetch venues
  const { data: venues, isLoading: venuesLoading } = useVenues();

  // Fetch instances for selected venue
  const { data: instances, isLoading: instancesLoading } = useInstances(
    selectedVenue ? { venue: selectedVenue } : undefined
  );

  // Fetch dashboard data
  const {
    data: dashboardData,
    isLoading: dashboardLoading,
    error: dashboardError
  } = useDashboard({
    ...(selectedInstance ? { instance: selectedInstance } : {}),
    ...(selectedVenue && selectedYear ? { venue: selectedVenue, year: selectedYear } : {}),
    page: currentPage,
    page_size: 20
  });

  // Fetch overview data
  const { data: overviewData } = useOverview();

  const handleVenueChange = (venue: string) => {
    setSelectedVenue(venue);
    setSelectedYear(undefined);
    setSelectedInstance(undefined);
    setCurrentPage(1);
  };

  const handleYearChange = (year: number) => {
    setSelectedYear(year);
    setSelectedInstance(undefined);
    setCurrentPage(1);
  };

  const handleInstanceSelect = (instanceId: number) => {
    setSelectedInstance(instanceId);
    setCurrentPage(1);
  };

  const availableYears = instances
    ? [...new Set(instances.map(i => i.year))].sort((a, b) => b - a)
    : [];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-8">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-4">
              Conference Publications Dashboard
            </h1>

            {/* Overview Stats */}
            {overviewData && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div className="bg-white p-6 rounded-lg shadow-sm border">
                  <h3 className="text-sm font-medium text-gray-600">Total Conferences</h3>
                  <p className="text-2xl font-bold text-gray-900">{overviewData.total_conferences}</p>
                </div>
                <div className="bg-white p-6 rounded-lg shadow-sm border">
                  <h3 className="text-sm font-medium text-gray-600">Total Papers</h3>
                  <p className="text-2xl font-bold text-gray-900">{overviewData.total_papers.toLocaleString()}</p>
                </div>
                <div className="bg-white p-6 rounded-lg shadow-sm border">
                  <h3 className="text-sm font-medium text-gray-600">Years Covered</h3>
                  <p className="text-2xl font-bold text-gray-900">{overviewData.years_covered.length}</p>
                </div>
                <div className="bg-white p-6 rounded-lg shadow-sm border">
                  <h3 className="text-sm font-medium text-gray-600">Avg Papers/Year</h3>
                  <p className="text-2xl font-bold text-gray-900">{Math.round(overviewData.avg_papers_per_year)}</p>
                </div>
              </div>
            )}
          </div>

          {/* Selectors */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Select Conference & Year</h2>
            <div className="flex flex-wrap gap-4">
              {/* Venue Selector */}
              <div className="min-w-48">
                <select
                  value={selectedVenue}
                  onChange={(e) => handleVenueChange(e.target.value)}
                  disabled={venuesLoading}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
                >
                  <option value="">Select Conference</option>
                  {venues?.map((venue) => (
                    <option key={venue.id} value={venue.name}>
                      {venue.name} ({venue.type})
                    </option>
                  ))}
                </select>
              </div>

              {/* Year Selector */}
              {selectedVenue && (
                <div className="min-w-36">
                  <select
                    value={selectedYear || ''}
                    onChange={(e) => handleYearChange(Number(e.target.value))}
                    disabled={instancesLoading}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
                  >
                    <option value="">Select Year</option>
                    {availableYears.map((year) => (
                      <option key={year} value={year}>
                        {year}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Quick Instance Selector */}
              {instances && instances.length > 0 && (
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-700 mb-2">Quick Select:</div>
                  <div className="flex flex-wrap gap-2">
                    {instances.slice(0, 5).map((instance) => (
                      <button
                        key={instance.instance_id}
                        onClick={() => handleInstanceSelect(instance.instance_id)}
                        className={`px-3 py-2 text-sm rounded-lg border transition-colors ${
                          selectedInstance === instance.instance_id
                            ? 'bg-blue-600 text-white border-blue-600'
                            : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        {instance.venue.name} {instance.year}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Dashboard Content */}
          {dashboardError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center">
                <AlertCircle className="h-5 w-5 text-red-400 mr-2" />
                <span className="text-red-800">
                  Error loading dashboard data. Please check your selection and try again.
                </span>
              </div>
            </div>
          )}

          {dashboardData && (
            <div className="space-y-8">
              {/* KPIs */}
              <DashboardKPIs data={dashboardData.kpis} isLoading={dashboardLoading} />

              {/* Charts */}
              <DashboardCharts data={dashboardData.charts} isLoading={dashboardLoading} />

              {/* Publications Table */}
              <PublicationsTable
                data={dashboardData.table}
                pagination={dashboardData.pagination}
                currentPage={currentPage}
                onPageChange={setCurrentPage}
                isLoading={dashboardLoading}
              />
            </div>
          )}

          {/* No Selection State */}
          {!selectedInstance && (!selectedVenue || !selectedYear) && !dashboardLoading && (
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
  );
}