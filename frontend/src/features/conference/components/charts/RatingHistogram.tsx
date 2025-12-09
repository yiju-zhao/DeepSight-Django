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
          <h3 className="text-lg font-bold text-[#1E1E1E]">Rating Distribution</h3>
          <div className="w-32 h-8 bg-[#F5F5F5] rounded animate-pulse"></div>
        </div>
        <div className="w-full h-80 bg-[#FAFAFA] rounded-lg animate-pulse flex items-center justify-center">
          <div className="text-[#999999]">Loading...</div>
        </div>
      </div>
    );
  }

  if (!data?.length) {
    return (
      <div className="w-full">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-bold text-[#1E1E1E]">Rating Distribution</h3>
          <select
            value={selectedBinSize}
            onChange={(e) => handleBinSizeChange(parseFloat(e.target.value))}
            className="px-3 py-1 border border-[#E3E3E3] rounded text-sm text-[#666666] focus:outline-none focus:border-[#000000]"
          >
            <option value={0.25}>Bin: 0.25</option>
            <option value={0.5}>Bin: 0.5</option>
            <option value={1.0}>Bin: 1.0</option>
          </select>
        </div>
        <div className="w-full h-80 bg-[#FAFAFA] rounded-lg flex items-center justify-center border border-dashed border-[#E3E3E3]">
          <div className="text-[#999999]">No rating data available</div>
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
    <div className="w-full h-full flex flex-col">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-bold text-[#1E1E1E]">Rating Distribution</h3>
        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium text-[#666666]">Bin Size:</label>
          <select
            value={selectedBinSize}
            onChange={(e) => handleBinSizeChange(parseFloat(e.target.value))}
            className="px-3 py-1 border border-[#E3E3E3] rounded text-sm text-[#1E1E1E] focus:outline-none focus:border-[#000000] bg-white cursor-pointer hover:border-[#999999]"
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
          margin={{ top: 10, right: 30, bottom: 50, left: 50 }}
          colors={['#000000']} // Solid Black Bars
          axisBottom={{
            tickSize: 0,
            tickPadding: 12,
            tickRotation: 0,
            legend: 'Rating Range',
            legendPosition: 'middle',
            legendOffset: 40
          }}
          axisLeft={{
            tickSize: 0,
            tickPadding: 12,
            tickRotation: 0,
            legend: 'Count',
            legendPosition: 'middle',
            legendOffset: -40
          }}
          tooltip={({ data }) => (
            <div className="bg-white p-3 shadow-lg rounded border border-[#E3E3E3]">
              <div className="font-bold text-[#1E1E1E] text-sm mb-1">
                Rating: {data.binStart?.toFixed(1)} - {data.binEnd?.toFixed(1)}
              </div>
              <div className="text-sm text-[#666666]">
                <span className="font-bold text-[#CE0E2D]">{data.value}</span> publications
              </div>
            </div>
          )}
        />
      </div>
    </div>
  );
};

export const RatingHistogram = memo(RatingHistogramComponent);
