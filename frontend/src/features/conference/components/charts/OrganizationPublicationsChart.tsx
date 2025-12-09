import { memo, useState } from 'react';
import { ResponsiveBar } from '@nivo/bar';
import { ChevronDown } from 'lucide-react';
import { OrganizationPublicationData, OrganizationPublicationByResearchAreaData } from '../../types';
import chartTheme from '../../utils/chartTheme';

interface OrganizationPublicationsChartProps {
  data: OrganizationPublicationData[];
  stackedData: OrganizationPublicationByResearchAreaData[];
  isLoading?: boolean;
}

type ViewMode = 'total' | 'research_area';

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
          className="inline-flex justify-center w-full rounded-md border border-[#E3E3E3] shadow-sm px-4 py-2 bg-white text-sm font-medium text-[#1E1E1E] hover:bg-[#F5F5F5] focus:outline-none focus:ring-1 focus:ring-[#000000]"
          onClick={() => setIsOpen(!isOpen)}
        >
          {currentOption?.label}
          <ChevronDown className={`-mr-1 ml-2 h-5 w-5 transform transition-transform text-[#666666] ${isOpen ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {isOpen && (
        <div className="origin-top-right absolute right-0 mt-2 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 focus:outline-none z-10 border border-[#E3E3E3]">
          <div className="py-1">
            {options.map((option) => (
              <button
                key={option.value}
                onClick={() => {
                  onViewModeChange(option.value);
                  setIsOpen(false);
                }}
                className={`${viewMode === option.value
                  ? 'bg-[#F5F5F5] text-[#000000] font-medium'
                  : 'text-[#666666]'
                  } block px-4 py-2 text-sm hover:bg-[#F5F5F5] hover:text-[#000000] w-full text-left`}
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
      <div className="w-full h-[500px] bg-[#FAFAFA] rounded-lg animate-pulse flex items-center justify-center border border-[#E3E3E3]">
        <div className="text-[#999999]">Loading...</div>
      </div>
    );
  }

  if (!data?.length) {
    return (
      <div className="w-full h-[500px] bg-[#FAFAFA] rounded-lg flex items-center justify-center border border-dashed border-[#E3E3E3]">
        <div className="text-[#999999]">No organization publication data available</div>
      </div>
    );
  }

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
      if (!stackedData?.length) return { data: [], keys: [] };

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

  // Use Grayscale + Red for stacked bars
  const stackedColors = [
    '#000000', '#333333', '#666666', '#999999', '#CCCCCC', '#CE0E2D'
  ];

  return (
    <div className="w-full">
      <ViewModeSelector viewMode={viewMode} onViewModeChange={setViewMode} />
      <div className="w-full h-[500px]">
        <ResponsiveBar
          data={chartData}
          keys={keys}
          indexBy="organization"
          layout="vertical"
          {...chartTheme.barChart}
          legends={[
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
              ]
            }
          ]}
          margin={{
            top: 20,
            right: viewMode === 'total' ? 60 : 180,
            bottom: 150,
            left: 60
          }}
          padding={0.2}
          colors={viewMode === 'total' ? ['#000000'] : stackedColors} // Solid black for total
          axisBottom={{
            tickSize: 0,
            tickPadding: 16,
            tickRotation: -45, // Angled labels for better fit
            legend: '',
            legendPosition: 'middle',
            legendOffset: 100
          }}
          axisLeft={{
            tickSize: 0,
            tickPadding: 12,
            tickRotation: 0,
            legend: 'Count',
            legendPosition: 'middle',
            legendOffset: -40
          }}
          enableLabel={viewMode === 'total'}
          tooltip={({ id, value, indexValue, color }) => (
            <div className="bg-white p-3 shadow-lg rounded-lg border border-[#E3E3E3]">
              <div className="font-bold text-[#1E1E1E] text-sm mb-1">
                {indexValue}
              </div>
              {viewMode === 'research_area' && (
                <div className="flex items-center text-sm text-[#666666]">
                  <div
                    className="w-3 h-3 mr-2 rounded-sm flex-shrink-0"
                    style={{ backgroundColor: color }}
                  />
                  <span className="text-xs text-[#999999] mr-2">{id}:</span>
                  <span className="font-medium text-[#1E1E1E]">{value}</span>
                </div>
              )}
              {viewMode === 'total' && (
                <div className="text-sm text-[#666666]">
                  <span className="font-bold text-[#CE0E2D]">{value}</span> publications
                </div>
              )}
            </div>
          )}
        />
      </div>
    </div>
  );
};

export const OrganizationPublicationsChart = memo(OrganizationPublicationsChartComponent);
