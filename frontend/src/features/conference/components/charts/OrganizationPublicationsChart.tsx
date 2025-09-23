import { memo } from 'react';
import { ResponsiveBar } from '@nivo/bar';
import { OrganizationPublicationData } from '../../types';

interface OrganizationPublicationsChartProps {
  data: OrganizationPublicationData[];
  isLoading?: boolean;
}

const OrganizationPublicationsChartComponent = ({ data, isLoading }: OrganizationPublicationsChartProps) => {
  if (isLoading) {
    return (
      <div className="w-full h-[500px] bg-gray-100 rounded-lg animate-pulse flex items-center justify-center">
        <div className="text-gray-500">Loading organization publications...</div>
      </div>
    );
  }

  if (!data?.length) {
    return (
      <div className="w-full h-[500px] bg-gray-50 rounded-lg flex items-center justify-center">
        <div className="text-gray-500">No organization publication data available</div>
      </div>
    );
  }

  const sortedData = [...data].sort((a, b) => b.total - a.total);
  const chartData = sortedData.map(org => ({
    organization: org.organization,
    total: org.total
  }));

  return (
    <div className="w-full h-[500px]">
      <ResponsiveBar
        data={chartData}
        keys={['total']}
        indexBy="organization"
        layout="vertical"
        margin={{ top: 50, right: 130, bottom: 150, left: 60 }}
        padding={0.3}
        valueScale={{ type: 'linear' }}
        indexScale={{ type: 'band', round: true }}
        colors={{ scheme: 'nivo' }}
        borderColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
        axisTop={null}
        axisRight={null}
        axisBottom={{
          tickSize: 5,
          tickPadding: 5,
          tickRotation: -45,
          legend: '',
          legendPosition: 'middle',
          legendOffset: 100
        }}
        axisLeft={{
          tickSize: 5,
          tickPadding: 5,
          tickRotation: 0,
          legend: 'Publication Count',
          legendPosition: 'middle',
          legendOffset: -40
        }}
        enableLabel={true}
        labelSkipWidth={12}
        labelSkipHeight={12}
        labelTextColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
        legends={[]}
        tooltip={({ value, indexValue }) => (
          <div className="bg-white p-3 shadow-lg rounded-lg border">
            <div className="font-semibold text-gray-900">
              {indexValue}
            </div>
            <div className="text-sm text-gray-600">
              {value} publications (including collaborations)
            </div>
          </div>
        )}
        animate={true}
        motionConfig="gentle"
      />
    </div>
  );
};

export const OrganizationPublicationsChart = memo(OrganizationPublicationsChartComponent);
