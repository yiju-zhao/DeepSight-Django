import { memo, useState } from 'react';
import { ResponsiveBar } from '@nivo/bar';
import { ChevronDown } from 'lucide-react';
import { OrganizationPublicationData, OrganizationPublicationByResearchAreaData } from '../../types';

interface OrganizationPublicationsChartProps {
  data: OrganizationPublicationData[];
  stackedData: OrganizationPublicationByResearchAreaData[];
  isLoading?: boolean;
}

type ViewMode = 'total' | 'research_area';

// Utility function to convert snake_case to Title Case
const formatResearchAreaLabel = (area: string): string => {
  return area
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

const ViewModeSelector = ({ viewMode, onViewModeChange }: {
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const options = [
    { value: 'total' as ViewMode, label: 'Total Publications' },
    { value: 'research_area' as ViewMode, label: 'By Research Area' }
  ];

  const currentOption = options.find(opt => opt.value === viewMode);

  return (
    <div className="relative inline-block text-left mb-4">
      <div>
        <button
          type="button"
          className="inline-flex justify-center w-full rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          onClick={() => setIsOpen(!isOpen)}
        >
          {currentOption?.label}
          <ChevronDown className={`-mr-1 ml-2 h-5 w-5 transform transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {isOpen && (
        <div className="origin-top-right absolute right-0 mt-2 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 focus:outline-none z-10">
          <div className="py-1">
            {options.map((option) => (
              <button
                key={option.value}
                onClick={() => {
                  onViewModeChange(option.value);
                  setIsOpen(false);
                }}
                className={`${
                  viewMode === option.value
                    ? 'bg-gray-100 text-gray-900'
                    : 'text-gray-700'
                } block px-4 py-2 text-sm hover:bg-gray-100 hover:text-gray-900 w-full text-left`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const OrganizationPublicationsChartComponent = ({ data, stackedData, isLoading }: OrganizationPublicationsChartProps) => {
  const [viewMode, setViewMode] = useState<ViewMode>('total');

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

  // Prepare data based on view mode
  const prepareChartData = () => {
    if (viewMode === 'total') {
      const sortedData = [...data].sort((a, b) => b.total - a.total);
      return {
        data: sortedData.map(org => ({
          organization: org.organization,
          total: org.total
        })),
        keys: ['total']
      };
    } else {
      // Research area mode - use stacked data
      if (!stackedData?.length) return { data: [], keys: [] };

      // Transform data to use formatted labels as keys
      const transformedData = stackedData.map(org => {
        const transformedOrg: any = { organization: org.organization };
        Object.keys(org).forEach(key => {
          if (key !== 'organization') {
            const formattedKey = formatResearchAreaLabel(key);
            transformedOrg[formattedKey] = org[key];
          }
        });
        return transformedOrg;
      });

      // Extract all possible research area keys (excluding 'organization')
      const allKeys = new Set<string>();
      transformedData.forEach(org => {
        Object.keys(org).forEach(key => {
          if (key !== 'organization') {
            allKeys.add(key);
          }
        });
      });

      return {
        data: transformedData,
        keys: Array.from(allKeys)
      };
    }
  };

  const { data: chartData, keys } = prepareChartData();

  if (!chartData.length) {
    return (
      <div className="w-full">
        <ViewModeSelector viewMode={viewMode} onViewModeChange={setViewMode} />
        <div className="w-full h-[500px] bg-gray-50 rounded-lg flex items-center justify-center">
          <div className="text-gray-500">
            {viewMode === 'research_area'
              ? 'No research area data available'
              : 'No organization publication data available'
            }
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full">
      <ViewModeSelector viewMode={viewMode} onViewModeChange={setViewMode} />
      <div className="w-full h-[500px]">
        <ResponsiveBar
          data={chartData}
          keys={keys}
          indexBy="organization"
          layout="vertical"
          margin={{
            top: 20,
            right: viewMode === 'total' ? 60 : 180,
            bottom: 150,
            left: 60
          }}
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
            tickRotation: -20,
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
          enableLabel={viewMode === 'total'}
          labelSkipWidth={12}
          labelSkipHeight={12}
          labelTextColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
          legends={viewMode === 'research_area' ? [
            {
              dataFrom: 'keys',
              anchor: 'bottom-right',
              direction: 'column',
              justify: false,
              translateX: 120,
              translateY: 0,
              itemsSpacing: 2,
              itemWidth: 100,
              itemHeight: 20,
              itemDirection: 'left-to-right',
              itemOpacity: 0.85,
              symbolSize: 20,
              effects: [
                {
                  on: 'hover',
                  style: {
                    itemOpacity: 1
                  }
                }
              ],
              // Custom legend label formatting
              itemTextColor: '#333'
            }
          ] : []}
          tooltip={({ id, value, indexValue, color }) => (
            <div className="bg-white p-3 shadow-lg rounded-lg border">
              <div className="font-semibold text-gray-900">
                {indexValue}
              </div>
              {viewMode === 'research_area' && (
                <div
                  className="flex items-center text-sm text-gray-600 mb-1"
                >
                  <div
                    className="w-3 h-3 mr-2 rounded"
                    style={{ backgroundColor: color }}
                  />
                  {id}: {value} publications
                </div>
              )}
              {viewMode === 'total' && (
                <div className="text-sm text-gray-600">
                  {value} publications (including collaborations)
                </div>
              )}
            </div>
          )}
          animate={true}
          motionConfig="gentle"
        />
      </div>
    </div>
  );
};

export const OrganizationPublicationsChart = memo(OrganizationPublicationsChartComponent);
