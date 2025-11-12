import { memo, useState } from 'react';
import { ResponsiveBar } from '@nivo/bar';
import { FineHistogramBin } from '../../types';
import chartTheme from '../../utils/chartTheme';

interface RatingHistogramProps {
  data: FineHistogramBin[];
  isLoading?: boolean;
  onBinSizeChange?: (binSize: number) => void;
  currentBinSize?: number;
}

const RatingHistogramComponent = ({
  data,
  isLoading,
  onBinSizeChange,
  currentBinSize = 0.5
}: RatingHistogramProps) => {
  const [selectedBinSize, setSelectedBinSize] = useState(currentBinSize);

  const handleBinSizeChange = (newBinSize: number) => {
    setSelectedBinSize(newBinSize);
    onBinSizeChange?.(newBinSize);
  };

  if (isLoading) {
    return (
      <div className="w-full">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">Rating Distribution (Fine-Grained)</h3>
          <div className="w-32 h-8 bg-gray-200 rounded animate-pulse"></div>
        </div>
        <div className="w-full h-80 bg-gray-100 rounded-lg animate-pulse flex items-center justify-center">
          <div className="text-gray-500">Loading rating distribution...</div>
        </div>
      </div>
    );
  }

  if (!data?.length) {
    return (
      <div className="w-full">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">Rating Distribution (Fine-Grained)</h3>
          <select
            value={selectedBinSize}
            onChange={(e) => handleBinSizeChange(parseFloat(e.target.value))}
            className="px-3 py-1 border border-gray-300 rounded-md text-sm"
          >
            <option value={0.25}>Bin Size: 0.25</option>
            <option value={0.5}>Bin Size: 0.5</option>
            <option value={1.0}>Bin Size: 1.0</option>
          </select>
        </div>
        <div className="w-full h-80 bg-gray-50 rounded-lg flex items-center justify-center">
          <div className="text-gray-500">No rating data available</div>
        </div>
      </div>
    );
  }

  const chartData = data.map(bin => ({
    id: `${bin.start.toFixed(1)}-${bin.end.toFixed(1)}`,
    label: `${bin.start.toFixed(1)}`,
    value: bin.count,
    binStart: bin.start,
    binEnd: bin.end
  }));

  return (
    <div className="w-full">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Rating Distribution (Fine-Grained)</h3>
        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium text-gray-700">Bin Size:</label>
          <select
            value={selectedBinSize}
            onChange={(e) => handleBinSizeChange(parseFloat(e.target.value))}
            className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value={0.25}>0.25</option>
            <option value={0.5}>0.5</option>
            <option value={1.0}>1.0</option>
          </select>
        </div>
      </div>

      <div className="w-full h-80">
        <ResponsiveBar
          data={chartData}
          keys={['value']}
          indexBy="label"
          {...chartTheme.barChart}
          margin={{ top: 20, right: 60, bottom: 50, left: 60 }}
          padding={0.15}
          valueScale={{ type: 'linear' }}
          indexScale={{ type: 'band', round: true }}
          colors={[chartTheme.colors[0]]}
          borderRadius={4}
          axisTop={null}
          axisRight={null}
          axisBottom={{
            tickSize: 5,
            tickPadding: 5,
            tickRotation: 0,
            legend: 'Rating Range',
            legendPosition: 'middle',
            legendOffset: 36
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
          labelTextColor={{ from: 'color', modifiers: [['darker', 1.8]] }}
          tooltip={({ data }) => (
            <div className="bg-white p-3 shadow-lg rounded-lg border border-gray-200">
              <div className="font-semibold text-gray-900 text-sm mb-1">
                Rating: {data.binStart?.toFixed(1)} - {data.binEnd?.toFixed(1)}
              </div>
              <div className="text-sm text-gray-600">
                <span className="font-medium text-gray-900">{data.value}</span> publications
              </div>
            </div>
          )}
          animate={true}
          motionConfig="gentle"
        />
      </div>
    </div>
  );
};

export const RatingHistogram = memo(RatingHistogramComponent);
