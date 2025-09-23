import { Text } from '@visx/text';
import { scaleLog } from '@visx/scale';
import Wordcloud from '@visx/wordcloud/lib/Wordcloud';
import { ResponsiveChord } from '@nivo/chord';
import { ResponsiveBar } from '@nivo/bar';
import { ChartData, FineHistogramBin, OrganizationPublicationData, ForceGraphData } from '../types';
import { memo, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Maximize2, X } from 'lucide-react';

interface DashboardChartsProps {
  data: ChartData;
  isLoading?: boolean;
  ratingHistogramData?: FineHistogramBin[];
  ratingHistogramLoading?: boolean;
  onBinSizeChange?: (binSize: number) => void;
  currentBinSize?: number;
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#84CC16'];

const fixedValueGenerator = () => 0.5;

function WordCloudComponent({ keywords }: { keywords: Array<{ name: string; count: number }> }) {
  const words = keywords.map(keyword => ({
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

  const fontSizeSetter = (datum: { text: string; value: number }) => fontScale(datum.value);

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

const TopOrgChordTop10 = memo(({ data, isLoading }: { data: { keys: string[]; matrix: number[][] }; isLoading?: boolean }) => {
  if (isLoading) {
    return (
      <div className="w-full h-[600px] bg-gray-100 rounded-lg animate-pulse flex items-center justify-center">
        <div className="text-gray-500">Loading organization collaboration...</div>
      </div>
    );
  }

  if (!data?.keys?.length || !data?.matrix?.length) {
    return (
      <div className="w-full h-[600px] bg-gray-50 rounded-lg flex items-center justify-center">
        <div className="text-gray-500">No organization collaboration data available</div>
      </div>
    );
  }

  return (
    <div className="w-full h-[600px]">
      <ResponsiveChord
        data={data.matrix}
        keys={data.keys}
        margin={{ top: 60, right: 60, bottom: 90, left: 60 }}
        padAngle={0.04}
        innerRadiusRatio={0.94}
        innerRadiusOffset={0.02}
        arcOpacity={0.7}
        arcBorderWidth={1}
        arcBorderColor={{ from: 'color', modifiers: [['darker', 0.3]] }}
        ribbonOpacity={0.45}
        ribbonBorderWidth={1}
        ribbonBorderColor={{ from: 'color', modifiers: [['darker', 0.5]] }}
        enableLabel={true}
        labelOffset={20}
        labelRotation={0}
        labelTextColor={{ from: 'color', modifiers: [['darker', 1]] }}
        colors={{ scheme: 'category10' }}
      />
    </div>
  );
});

const RatingHistogramFine = memo(({
  data,
  isLoading,
  onBinSizeChange,
  currentBinSize = 0.5
}: {
  data: FineHistogramBin[];
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

const OrganizationPublicationsChart = memo(({ data, isLoading }: { data: OrganizationPublicationData[]; isLoading?: boolean }) => {
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
        margin={{ top: 50, right: 130, bottom: 120, left: 60 }}
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
});

const GeographicCollaborationNetwork = memo(({ data, isLoading }: { data: ForceGraphData; isLoading?: boolean }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (isLoading) {
    return (
      <div className="w-full h-[600px] bg-gray-100 rounded-lg animate-pulse flex items-center justify-center">
        <div className="text-gray-500">Loading geographic collaboration network...</div>
      </div>
    );
  }

  if (!data?.nodes?.length || !data?.links?.length) {
    return (
      <div className="w-full h-[600px] bg-gray-50 rounded-lg flex items-center justify-center">
        <div className="text-gray-500">No geographic collaboration data available</div>
      </div>
    );
  }

  const NetworkChart = ({ width, height, fontSize, zoom = 2 }: {
    width: number;
    height: number;
    fontSize: number;
    zoom?: number;
  }) => (
    <ForceGraph2D
      graphData={data}
      width={width}
      height={height}
      nodeLabel="id"
      nodeAutoColorBy="group"
      linkDirectionalParticles="value"
      linkDirectionalParticleSpeed={d => d.value * 0.001}
      nodeRelSize={0}
      linkWidth={d => Math.sqrt(d.value) * 2}
      linkDirectionalParticleWidth={4}
      backgroundColor="#ffffff"
      zoom={zoom}
      nodeCanvasObject={(node, ctx, globalScale) => {
        const label = node.id;
        const adjustedFontSize = fontSize/globalScale;
        ctx.font = `${adjustedFontSize}px Sans-Serif`;
        const textWidth = ctx.measureText(label).width;
        const bckgDimensions = [textWidth, adjustedFontSize].map(n => n + adjustedFontSize * 0.2);

        if (typeof node.x === 'number' && typeof node.y === 'number' && bckgDimensions.length === 2 && typeof bckgDimensions[0] === 'number' && typeof bckgDimensions[1] === 'number') {
          // Draw background
          ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
          ctx.fillRect(
            node.x - bckgDimensions[0] / 2,
            node.y - bckgDimensions[1] / 2,
            bckgDimensions[0],
            bckgDimensions[1]
          );

          // Draw text
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = node.color || '#333';
          ctx.fillText(label, node.x, node.y);

          // Store dimensions for click area
          (node as any).__bckgDimensions = bckgDimensions;
        }
      }}
      nodePointerAreaPaint={(node, color, ctx) => {
        ctx.fillStyle = color;
        const bckgDimensions = (node as any).__bckgDimensions;
        if (bckgDimensions && Array.isArray(bckgDimensions) && bckgDimensions.length === 2 && typeof bckgDimensions[0] === 'number' && typeof bckgDimensions[1] === 'number' && typeof node.x === 'number' && typeof node.y === 'number') {
          ctx.fillRect(
            node.x - bckgDimensions[0] / 2,
            node.y - bckgDimensions[1] / 2,
            bckgDimensions[0],
            bckgDimensions[1]
          );
        }
      }}
      cooldownTicks={100}
      onEngineStop={() => {}}
      d3AlphaDecay={0.02}
      d3VelocityDecay={0.08}
    />
  );

  if (isExpanded) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl w-[95vw] h-[95vh] flex flex-col">
          <div className="flex items-center justify-between p-4 border-b">
            <h3 className="text-xl font-semibold text-gray-900">Geographic Collaboration Network</h3>
            <button
              onClick={() => setIsExpanded(false)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-6 h-6 text-gray-600" />
            </button>
          </div>
          <div className="flex-1 flex items-center justify-center p-2">
            <NetworkChart
              width={window.innerWidth * 0.9}
              height={window.innerHeight * 0.8}
              fontSize={16}
              zoom={1.5}
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full flex items-center justify-center">
      <button
        onClick={() => setIsExpanded(true)}
        className="absolute top-2 right-2 p-2 hover:bg-gray-100 rounded-lg transition-colors z-10"
        title="Expand to full screen"
      >
        <Maximize2 className="w-5 h-5 text-gray-600" />
      </button>
      <NetworkChart
        width={460}
        height={510}
        fontSize={12}
        zoom={2.5}
      />
    </div>
  );
});

const ChartCard = ({
  title,
  children,
  isLoading,
  height = "h-80"
}: {
  title: string;
  children: React.ReactNode;
  isLoading?: boolean;
  height?: string;
}) => {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="h-5 bg-gray-200 rounded animate-pulse w-48 mb-4" />
        <div className={`${height} bg-gray-200 rounded animate-pulse`} />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      <div className={height}>
        {children}
      </div>
    </div>
  );
};

const DashboardChartsComponent = ({ data, isLoading, ratingHistogramData, ratingHistogramLoading, onBinSizeChange, currentBinSize = 0.5 }: DashboardChartsProps) => {
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
          <RatingHistogramFine
            data={ratingHistogramData || data.ratings_histogram_fine || []}
            isLoading={ratingHistogramLoading}
            onBinSizeChange={onBinSizeChange}
            currentBinSize={currentBinSize}
          />
        </ChartCard>
        <ChartCard title="Popular Keywords">
          <WordCloudComponent keywords={data.top_keywords || []} />
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
          <GeographicCollaborationNetwork
            data={data.force_graphs?.country || { nodes: [], links: [] }}
            isLoading={isLoading}
          />
        </ChartCard>
        <ChartCard title="Organization Collaboration (Top 10)" height="h-[550px]">
          <TopOrgChordTop10
            data={data.chords?.org || { keys: [], matrix: [] }}
            isLoading={isLoading}
          />
        </ChartCard>
      </div>
    </div>
  );
};

DashboardChartsComponent.displayName = 'DashboardCharts';

export const DashboardCharts = memo(DashboardChartsComponent);