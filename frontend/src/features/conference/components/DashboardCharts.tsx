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
      <div className="space-y-8">
        <div className="h-7 bg-[#F5F5F5] rounded animate-pulse w-48" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {Array.from({ length: 4 }).map((_, i) => (
            <ChartCard key={i} title="" isLoading={true}>
              <div />
            </ChartCard>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Rating Histogram and Keywords - 2 Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
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

      {/* Organization Publications - Full Width */}
      <div className="grid grid-cols-1 gap-8">
        <ChartCard title="Organization Publications (Top 15)" height="h-[500px]">
          <OrganizationPublicationsChart
            data={data.organization_publications || []}
            stackedData={data.organization_publications_by_research_area || []}
            isLoading={isLoading}
          />
        </ChartCard>
      </div>

      {/* Collaboration Networks - 2 Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <ChartCard title="Geographic Collaboration Network" height="h-[550px]">
          <NetworkGraph
            data={data.force_graphs?.country || { nodes: [], links: [] }}
            isLoading={isLoading}
            title="Geographic Collaboration Network"
            noDataMessage="No geographic collaboration data available"
            loadingMessage="Loading geographic collaboration network..."
            themeColor="orange"
          />
        </ChartCard>
        <ChartCard title="Organization Collaboration Network (Top 15)" height="h-[550px]">
          <NetworkGraph
            data={data.force_graphs?.organization || { nodes: [], links: [] }}
            isLoading={isLoading}
            title="Organization Collaboration Network"
            noDataMessage="No organization collaboration data available"
            loadingMessage="Loading organization collaboration network..."
            themeColor="purple"
          />
        </ChartCard>
      </div>
    </div>
  );
};

DashboardChartsComponent.displayName = 'DashboardCharts';

export const DashboardCharts = memo(DashboardChartsComponent);
