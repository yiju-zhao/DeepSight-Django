import { Text } from '@visx/text';
import { scaleLog } from '@visx/scale';
import Wordcloud from '@visx/wordcloud/lib/Wordcloud';
import { ResponsiveChord } from '@nivo/chord';
import { ResponsiveBar } from '@nivo/bar';
import { ChartData } from '../types';
import { memo, useState } from 'react';

interface DashboardChartsProps {
  data: ChartData;
  isLoading?: boolean;
  onBinSizeChange?: (binSize: number) => void;
  currentBinSize?: number;
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#84CC16'];

interface WordData {
  text: string;
  value: number;
}

interface ChordData {
  keys: string[];
  matrix: number[][];
}

interface HistogramBin {
  bin: number;
  start: number;
  end: number;
  count: number;
}

const fixedValueGenerator = () => 0.5;

interface WordCloudProps {
  keywords: Array<{ name: string; count: number }>;
}

function WordCloudComponent({ keywords }: WordCloudProps) {
  const words: WordData[] = keywords.map(keyword => ({
    text: keyword.name,
    value: keyword.count,
  }));

  if (words.length === 0) {
    return (
      <div className="w-full h-80 bg-gray-50 rounded-lg flex items-center justify-center">
        <div className="text-gray-500">No keyword data available</div>
      </div>
    );
  }

  const fontScale = scaleLog({
    domain: [Math.min(...words.map((w) => w.value)), Math.max(...words.map((w) => w.value))],
    range: [12, 60],
  });

  const fontSizeSetter = (datum: WordData) => fontScale(datum.value);

  return (
    <div style={{ width: '100%', height: '320px', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
      <Wordcloud
        words={words}
        width={500}
        height={320}
        fontSize={fontSizeSetter}
        font={'Inter, sans-serif'}
        padding={2}
        spiral="rectangular"
        rotate={0}
        random={fixedValueGenerator}
      >
        {(cloudWords) =>
          cloudWords.map((w, i) => (
            <Text
              key={w.text}
              fill={COLORS[i % COLORS.length]}
              textAnchor="middle"
              transform={`translate(${w.x}, ${w.y}) rotate(${w.rotate})`}
              fontSize={w.size}
              fontFamily={w.font}
              className="cursor-pointer hover:opacity-80 transition-opacity duration-200"
              style={{
                textShadow: '1px 1px 2px rgba(0,0,0,0.1)',
                fontWeight: 600,
              }}
            >
              {w.text}
            </Text>
          ))
        }
      </Wordcloud>
    </div>
  );
}

// Geographic Chord Component
const GeographicChordTop8 = memo(({ data, isLoading }: { data: ChordData; isLoading?: boolean }) => {
  if (isLoading) {
    return (
      <div className="w-full h-[500px] bg-gray-100 rounded-lg animate-pulse flex items-center justify-center">
        <div className="text-gray-500">Loading geographic collaboration...</div>
      </div>
    );
  }

  if (!data?.keys?.length || !data?.matrix?.length) {
    return (
      <div className="w-full h-[500px] bg-gray-50 rounded-lg flex items-center justify-center">
        <div className="text-gray-500">No collaboration data available</div>
      </div>
    );
  }

  return (
    <div className="w-full h-[500px]">
      <ResponsiveChord
        data={data.matrix}
        keys={data.keys}
        margin={{ top: 80, right: 140, bottom: 80, left: 60 }}
        padAngle={0.06}
        innerRadiusRatio={0.96}
        innerRadiusOffset={0.02}
        arcOpacity={0.6}
        arcBorderWidth={1}
        arcBorderColor={{ from: 'color', modifiers: [['darker', 0.4]] }}
        ribbonOpacity={0.5}
        ribbonBorderWidth={1}
        ribbonBorderColor={{ from: 'color', modifiers: [['darker', 0.4]] }}
        enableLabel={true}
        labelOffset={12}
        labelRotation={-45}
        labelTextColor={{ from: 'color', modifiers: [['darker', 1]] }}
        colors={{ scheme: 'category10' }}
        legends={[
          {
            anchor: 'right',
            direction: 'column',
            translateY: 0,
            itemWidth: 80,
            itemHeight: 16,
            symbolShape: 'circle'
          }
        ]}
      />
    </div>
  );
});

// Organization Chord Component
const TopOrgChordTop10 = memo(({ data, isLoading }: { data: ChordData; isLoading?: boolean }) => {
  if (isLoading) {
    return (
      <div className="w-full h-[500px] bg-gray-100 rounded-lg animate-pulse flex items-center justify-center">
        <div className="text-gray-500">Loading organization collaboration...</div>
      </div>
    );
  }

  if (!data?.keys?.length || !data?.matrix?.length) {
    return (
      <div className="w-full h-[500px] bg-gray-50 rounded-lg flex items-center justify-center">
        <div className="text-gray-500">No organization collaboration data available</div>
      </div>
    );
  }

  return (
    <div className="w-full h-[500px]">
      <ResponsiveChord
        data={data.matrix}
        keys={data.keys}
        margin={{ top: 80, right: 140, bottom: 80, left: 60 }}
        padAngle={0.04}
        innerRadiusRatio={0.94}
        innerRadiusOffset={0.02}
        arcOpacity={0.7}
        arcBorderWidth={1}
        arcBorderColor={{ from: 'color', modifiers: [['darker', 0.3]] }}
        ribbonOpacity={0.4}
        ribbonBorderWidth={1}
        ribbonBorderColor={{ from: 'color', modifiers: [['darker', 0.5]] }}
        enableLabel={true}
        labelOffset={16}
        labelRotation={-60}
        labelTextColor={{ from: 'color', modifiers: [['darker', 1]] }}
        colors={{ scheme: 'set2' }}
        legends={[
          {
            anchor: 'right',
            direction: 'column',
            translateY: 0,
            itemWidth: 80,
            itemHeight: 16,
            symbolShape: 'circle'
          }
        ]}
      />
    </div>
  );
});

// Rating Histogram Component
const RatingHistogramFine = memo(({
  data,
  isLoading,
  onBinSizeChange,
  currentBinSize = 0.5
}: {
  data: HistogramBin[];
  isLoading?: boolean;
  onBinSizeChange?: (binSize: number) => void;
  currentBinSize?: number;
}) => {
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

  // Prepare data for Nivo Bar
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
          margin={{ top: 20, right: 60, bottom: 50, left: 60 }}
          padding={0.1}
          valueScale={{ type: 'linear' }}
          indexScale={{ type: 'band', round: true }}
          colors={{ scheme: 'dark2' }}
          borderColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
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
          labelTextColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
          tooltip={({ data }) => (
            <div className="bg-white p-3 shadow-lg rounded-lg border">
              <div className="font-semibold text-gray-900">
                Rating: {data.binStart?.toFixed(1)} - {data.binEnd?.toFixed(1)}
              </div>
              <div className="text-sm text-gray-600">
                {data.value} publications
              </div>
            </div>
          )}
          animate={true}
          motionConfig="gentle"
        />
      </div>
    </div>
  );
});

const ChartCard = ({
  title,
  children,
  isLoading
}: {
  title: string;
  children: React.ReactNode;
  isLoading?: boolean;
}) => {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="h-5 bg-gray-200 rounded animate-pulse w-48 mb-4" />
        <div className="h-80 bg-gray-200 rounded animate-pulse" />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      <div className="h-80">
        {children}
      </div>
    </div>
  );
};

const DashboardChartsComponent = ({ data, isLoading, onBinSizeChange, currentBinSize = 0.5 }: DashboardChartsProps) => {
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

      {/* Rating and Keywords - Side by Side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Rating Distribution (Fine-Grained) */}
        <ChartCard title="">
          <RatingHistogramFine
            data={data.ratings_histogram_fine || []}
            isLoading={isLoading}
            onBinSizeChange={onBinSizeChange}
            currentBinSize={currentBinSize}
          />
        </ChartCard>

        {/* Popular Keywords - Word Cloud */}
        <ChartCard title="Popular Keywords">
          <WordCloudComponent keywords={data.top_keywords || []} />
        </ChartCard>
      </div>

      {/* Geographic Collaboration - Full Width */}
      <ChartCard title="Geographic Collaboration (Top 8)">
        <GeographicChordTop8
          data={data.chords?.country || { keys: [], matrix: [] }}
          isLoading={isLoading}
        />
      </ChartCard>

      {/* Organization Collaboration - Full Width */}
      <ChartCard title="Organization Collaboration (Top 10)">
        <TopOrgChordTop10
          data={data.chords?.org || { keys: [], matrix: [] }}
          isLoading={isLoading}
        />
      </ChartCard>
    </div>
  );
};

DashboardChartsComponent.displayName = 'DashboardCharts';

export const DashboardCharts = memo(DashboardChartsComponent);