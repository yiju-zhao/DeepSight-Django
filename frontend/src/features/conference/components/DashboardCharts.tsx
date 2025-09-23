import { memo } from 'react';
import { ChartData, FineHistogramBin } from '../types';
import {
  ChartCard,
  NetworkGraph,
  OrganizationPublicationsChart,
  RatingHistogram,
  WordCloudChart,
} from './charts';

interface DashboardChartsProps {
  data: ChartData;
  isLoading?: boolean;
  ratingHistogramData?: FineHistogramBin[];
  ratingHistogramLoading?: boolean;
  onBinSizeChange?: (binSize: number) => void;
  currentBinSize?: number;
}

const DashboardChartsComponent = ({
  data,
  isLoading,
  ratingHistogramData,
  ratingHistogramLoading,
  onBinSizeChange,
  currentBinSize = 0.5,
}: DashboardChartsProps) => {
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="mb-4">
          <div className="h-7 bg-gray-200 rounded animate-pulse w-48" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <ChartCard key={i} title="" isLoading={true}>
              <div />
            </ChartCard>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="mb-4">
        <h2 className="text-2xl font-bold text-gray-900">Visualizations</h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="">
          <RatingHistogram
            data={ratingHistogramData || data.ratings_histogram_fine || []}
            isLoading={ratingHistogramLoading}
            onBinSizeChange={onBinSizeChange}
            currentBinSize={currentBinSize}
          />
        </ChartCard>
        <ChartCard title="Popular Keywords">
          <WordCloudChart keywords={data.top_keywords || []} />
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 gap-6">
        <ChartCard title="Organization Publications (Top 15)" height="h-[500px]">
          <OrganizationPublicationsChart
            data={data.organization_publications || []}
            isLoading={isLoading}
          />
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Geographic Collaboration Network" height="h-[550px]">
          <NetworkGraph
            data={data.force_graphs?.country || { nodes: [], links: [] }}
            isLoading={isLoading}
            title="Geographic Collaboration Network"
            noDataMessage="No geographic collaboration data available"
            loadingMessage="Loading geographic collaboration network..."
          />
        </ChartCard>
        <ChartCard title="Organization Collaboration Network (Top 20)" height="h-[550px]">
          <NetworkGraph
            data={data.force_graphs?.organization || { nodes: [], links: [] }}
            isLoading={isLoading}
            title="Organization Collaboration Network"
            noDataMessage="No organization collaboration data available"
            loadingMessage="Loading organization collaboration network..."
            use3D={true}
          />
        </ChartCard>
      </div>
    </div>
  );
};

DashboardChartsComponent.displayName = 'DashboardCharts';

export const DashboardCharts = memo(DashboardChartsComponent);
