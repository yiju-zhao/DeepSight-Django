import { BarChart3, TrendingUp, Users, Globe } from 'lucide-react';
import { useOverview } from '@/features/conference/hooks/useConference';

interface ConferenceSectionProps {
  onNavigateToConferences: () => void;
}

export default function ConferenceSection({ onNavigateToConferences }: ConferenceSectionProps) {
  const { data: overviewData, isLoading } = useOverview();

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="h-6 bg-gray-200 rounded animate-pulse w-48" />
          <div className="h-8 bg-gray-200 rounded animate-pulse w-24" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="h-8 bg-gray-200 rounded animate-pulse mb-2" />
              <div className="h-4 bg-gray-200 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <BarChart3 className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Conference Analytics</h2>
            <p className="text-sm text-gray-600">Explore publication data and research trends</p>
          </div>
        </div>
        <button
          onClick={onNavigateToConferences}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          View Dashboard
        </button>
      </div>

      {overviewData ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <div className="flex items-center justify-center mb-2">
              <BarChart3 className="h-5 w-5 text-blue-600 mr-1" />
              <span className="text-2xl font-bold text-blue-600">
                {overviewData.total_conferences}
              </span>
            </div>
            <p className="text-sm text-gray-600">Conferences</p>
          </div>

          <div className="text-center p-4 bg-green-50 rounded-lg">
            <div className="flex items-center justify-center mb-2">
              <TrendingUp className="h-5 w-5 text-green-600 mr-1" />
              <span className="text-2xl font-bold text-green-600">
                {overviewData.total_papers.toLocaleString()}
              </span>
            </div>
            <p className="text-sm text-gray-600">Publications</p>
          </div>

          <div className="text-center p-4 bg-purple-50 rounded-lg">
            <div className="flex items-center justify-center mb-2">
              <Globe className="h-5 w-5 text-purple-600 mr-1" />
              <span className="text-2xl font-bold text-purple-600">
                {overviewData.years_covered.length}
              </span>
            </div>
            <p className="text-sm text-gray-600">Years Covered</p>
          </div>

          <div className="text-center p-4 bg-orange-50 rounded-lg">
            <div className="flex items-center justify-center mb-2">
              <Users className="h-5 w-5 text-orange-600 mr-1" />
              <span className="text-2xl font-bold text-orange-600">
                {Math.round(overviewData.avg_papers_per_year)}
              </span>
            </div>
            <p className="text-sm text-gray-600">Avg Papers/Year</p>
          </div>
        </div>
      ) : (
        <div className="text-center py-8">
          <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">Conference data is loading...</p>
        </div>
      )}

      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h3 className="font-medium text-gray-900 mb-2">Available Analysis</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
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
            Author Collaboration Networks
          </div>
        </div>
      </div>
    </div>
  );
}