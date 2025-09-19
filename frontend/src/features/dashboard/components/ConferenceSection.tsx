import { BarChart3, TrendingUp, Users, Globe } from 'lucide-react';
import { useOverview } from '@/features/conference/hooks/useConference';

interface ConferenceSectionProps {
  onNavigateToConferences: () => void;
}

export default function ConferenceSection({ onNavigateToConferences }: ConferenceSectionProps) {
  const { data: overviewData, isLoading } = useOverview();

  if (isLoading) {
    return (
      <div className="bg-white/70 backdrop-blur-sm rounded-xl border border-gray-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="h-6 bg-gray-200 rounded animate-pulse w-48" />
          <div className="h-8 bg-gray-200 rounded animate-pulse w-24" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="text-center p-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className="h-8 bg-gray-200 rounded animate-pulse mb-2" />
              <div className="h-4 bg-gray-200 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-xl border border-gray-200 p-6 shadow-sm hover:shadow-md transition h-full flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-gray-100 rounded-lg border border-gray-200">
            <BarChart3 className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-gray-900">Conference Analytics</h2>
            <p className="text-sm text-gray-600">Research data and trends</p>
          </div>
        </div>
      </div>

      <div className="flex-1">
        {overviewData ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="text-center p-3 bg-gray-50 rounded-lg border border-gray-200">
                <div className="flex items-center justify-center mb-1">
                  <BarChart3 className="h-4 w-4 text-blue-600 mr-1" />
                  <span className="text-xl font-bold text-blue-600">
                    {overviewData.total_conferences}
                  </span>
                </div>
                <p className="text-xs text-gray-600">Conferences</p>
              </div>

              <div className="text-center p-3 bg-gray-50 rounded-lg border border-gray-200">
                <div className="flex items-center justify-center mb-1">
                  <TrendingUp className="h-4 w-4 text-green-600 mr-1" />
                  <span className="text-xl font-bold text-green-600">
                    {overviewData.total_papers.toLocaleString()}
                  </span>
                </div>
                <p className="text-xs text-gray-600">Publications</p>
              </div>

              <div className="text-center p-3 bg-gray-50 rounded-lg border border-gray-200">
                <div className="flex items-center justify-center mb-1">
                  <Globe className="h-4 w-4 text-purple-600 mr-1" />
                  <span className="text-xl font-bold text-purple-600">
                    {overviewData.years_covered.length}
                  </span>
                </div>
                <p className="text-xs text-gray-600">Years Covered</p>
              </div>

              <div className="text-center p-3 bg-gray-50 rounded-lg border border-gray-200">
                <div className="flex items-center justify-center mb-1">
                  <Users className="h-4 w-4 text-orange-600 mr-1" />
                  <span className="text-xl font-bold text-orange-600">
                    {Math.round(overviewData.avg_papers_per_year)}
                  </span>
                </div>
                <p className="text-xs text-gray-600">Avg Papers/Year</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-8">
            <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500">Conference data is loading...</p>
          </div>
        )}
      </div>

      <div className="mt-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
        <h3 className="font-medium text-gray-900 mb-2 text-sm">Available Analysis</h3>
        <div className="space-y-2 text-xs">
          <div className="flex items-center text-gray-600">
            <div className="w-2 h-2 bg-blue-500 rounded-full mr-2" />
            Research Topic Trends
          </div>
          <div className="flex items-center text-gray-600">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-2" />
            Geographic Distribution
          </div>
          <div className="flex items-center text-gray-600">
            <div className="w-2 h-2 bg-purple-500 rounded-full mr-2" />
            Author Networks
          </div>
        </div>
      </div>

      <div className="mt-4">
        <button
          onClick={onNavigateToConferences}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm"
        >
          Explore Analytics
        </button>
      </div>
    </div>
  );
}
