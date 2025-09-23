import { Text } from '@visx/text';
import { scaleLog } from '@visx/scale';
import Wordcloud from '@visx/wordcloud/lib/Wordcloud';
import { ResponsiveChord } from '@nivo/chord';
import { ResponsiveBar } from '@nivo/bar';
import ForceGraph2D from 'react-force-graph-2d';
import { ChartData, FineHistogramBin, OrganizationPublicationData, ForceGraphData } from '../types';
import { memo, useState, useMemo, useCallback } from 'react';

interface DashboardChartsProps {
  data: ChartData;
  isLoading?: boolean;
  ratingHistogramData?: FineHistogramBin[];
  ratingHistogramLoading?: boolean;
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

// Geographic Force Graph Component
const GeographicForceGraph = memo(({ data, isLoading }: { data: ForceGraphData; isLoading?: boolean }) => {
  const [highlightNodes, setHighlightNodes] = useState(new Set());
  const [highlightLinks, setHighlightLinks] = useState(new Set());
  const [hoverNode, setHoverNode] = useState<any>(null);

  // Process data to add neighbor and link relationships
  const processedData = useMemo(() => {
    if (!data?.nodes?.length || !data?.links?.length) return data;

    const nodes = data.nodes.map(node => ({ ...node, neighbors: [], links: [] }));
    const links = data.links.map(link => ({ ...link }));

    // Cross-link node objects
    links.forEach((link: any) => {
      const a = nodes.find(n => n.id === link.source);
      const b = nodes.find(n => n.id === link.target);
      if (a && b) {
        (a as any).neighbors.push(b);
        (b as any).neighbors.push(a);
        (a as any).links.push(link);
        (b as any).links.push(link);
      }
    });

    return { nodes, links };
  }, [data]);

  // Calculate font size scaling based on publication counts
  const fontSizeScale = useMemo(() => {
    if (!data?.nodes?.length) return { min: 10, max: 20 };
    const values = data.nodes.map(n => n.val);
    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);
    return { min: 10, max: 24, minVal, maxVal };
  }, [data]);

  const updateHighlight = () => {
    setHighlightNodes(new Set(highlightNodes));
    setHighlightLinks(new Set(highlightLinks));
  };

  const handleNodeHover = useCallback((node: any) => {
    highlightNodes.clear();
    highlightLinks.clear();
    if (node) {
      highlightNodes.add(node);
      if (node.neighbors) {
        node.neighbors.forEach((neighbor: any) => highlightNodes.add(neighbor));
      }
      if (node.links) {
        node.links.forEach((link: any) => highlightLinks.add(link));
      }
    }
    setHoverNode(node || null);
    updateHighlight();
  }, [highlightNodes, highlightLinks]);

  const handleLinkHover = useCallback((link: any) => {
    highlightNodes.clear();
    highlightLinks.clear();
    if (link) {
      highlightLinks.add(link);
      highlightNodes.add(link.source);
      highlightNodes.add(link.target);
    }
    updateHighlight();
  }, [highlightNodes, highlightLinks]);

  // Node painting function - based on the examples
  const nodePaint = useCallback((node: any, color: string, ctx: CanvasRenderingContext2D) => {
    const { x, y } = node;
    const label = node.id;

    // Calculate font size proportional to publication count
    const { min, max, minVal, maxVal } = fontSizeScale;
    const safeMinVal = minVal ?? 1;
    const safeMaxVal = maxVal ?? 1;
    const normalizedVal = safeMaxVal > safeMinVal ? (node.val - safeMinVal) / (safeMaxVal - safeMinVal) : 0.5;
    const fontSize = min + (max - min) * normalizedVal;

    // Draw text background if highlighted
    const isHighlighted = highlightNodes.has(node);
    if (isHighlighted) {
      ctx.font = `${fontSize}px Sans-Serif`;
      const textWidth = ctx.measureText(label).width;
      const bckgWidth = textWidth + fontSize * 0.4;
      const bckgHeight = fontSize + fontSize * 0.4;

      ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
      ctx.fillRect(x - bckgWidth / 2, y - bckgHeight / 2, bckgWidth, bckgHeight);
    }

    // Draw text
    ctx.font = `${fontSize}px Sans-Serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = isHighlighted ? '#000' : color;
    ctx.fillText(label, x, y);
  }, [fontSizeScale, highlightNodes]);

  // Ring painting for highlighted nodes
  const paintRing = useCallback((node: any, ctx: CanvasRenderingContext2D) => {
    const { x, y } = node;
    const radius = 30;

    ctx.beginPath();
    ctx.arc(x, y, radius, 0, 2 * Math.PI, false);
    ctx.fillStyle = node === hoverNode ? 'rgba(255, 0, 0, 0.3)' : 'rgba(255, 165, 0, 0.3)';
    ctx.fill();
  }, [hoverNode]);

  if (isLoading) {
    return (
      <div className="w-full h-[600px] bg-gray-100 rounded-lg animate-pulse flex items-center justify-center">
        <div className="text-gray-500">Loading geographic collaboration...</div>
      </div>
    );
  }

  if (!data?.nodes?.length) {
    return (
      <div className="w-full h-[600px] bg-gray-50 rounded-lg flex items-center justify-center">
        <div className="text-gray-500">No collaboration data available</div>
      </div>
    );
  }

  return (
    <div className="w-full h-[600px]">
      <ForceGraph2D
        graphData={processedData}
        width={700}
        height={600}
        autoPauseRedraw={false}
        nodeRelSize={8}
        linkWidth={(link: any) => highlightLinks.has(link) ? Math.sqrt(link.value) * 2 : Math.sqrt(link.value)}
        linkDirectionalParticles={4}
        linkDirectionalParticleWidth={(link: any) => highlightLinks.has(link) ? 4 : 0}
        linkColor={(link: any) => highlightLinks.has(link) ? 'rgba(255, 100, 100, 0.8)' : 'rgba(100, 100, 100, 0.5)'}
        onNodeHover={handleNodeHover}
        onLinkHover={handleLinkHover}
        nodeLabel={(node: any) => `${node.id}: ${node.val} publications`}
        nodeCanvasObjectMode={(node: any) => highlightNodes.has(node) ? 'before' : undefined}
        nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D) => {
          // Draw highlight ring for highlighted nodes
          if (highlightNodes.has(node)) {
            paintRing(node, ctx);
          }
          // Always draw the text node
          nodePaint(node, '#333', ctx);
        }}
        nodePointerAreaPaint={nodePaint}
      />
    </div>
  );
});

// Organization Chord Component
const TopOrgChordTop10 = memo(({ data, isLoading }: { data: ChordData; isLoading?: boolean }) => {
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

// Rating Histogram Component
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

// Organization Publications Chart Component
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

  // Sort data by total publications (descending) - backend already sorts but ensure frontend consistency
  const sortedData = [...data].sort((a, b) => b.total - a.total);

  // Transform data to nivo format - use total count instead of breaking down by research area
  const chartData = sortedData.map(org => ({
    organization: org.organization,
    total: org.total
  }));

  // Use single key for total publications
  const keys = ['total'];


  return (
    <div className="w-full h-[500px]">
      <ResponsiveBar
        data={chartData}
        keys={keys}
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

      {/* Rating and Keywords - Side by Side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Rating Distribution (Fine-Grained) */}
        <ChartCard title="">
          <RatingHistogramFine
            data={ratingHistogramData || data.ratings_histogram_fine || []}
            isLoading={ratingHistogramLoading}
            onBinSizeChange={onBinSizeChange}
            currentBinSize={currentBinSize}
          />
        </ChartCard>

        {/* Popular Keywords - Word Cloud */}
        <ChartCard title="Popular Keywords">
          <WordCloudComponent keywords={data.top_keywords || []} />
        </ChartCard>
      </div>

      {/* Organization Publications - Full Width */}
      <div className="grid grid-cols-1 gap-6">
        <ChartCard title="Organization Publications (Top 15)" height="h-[500px]">
          <OrganizationPublicationsChart
            data={data.organization_publications || []}
            isLoading={isLoading}
          />
        </ChartCard>
      </div>

      {/* Geographic and Organization Collaboration - Side by Side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Geographic Collaboration Network" height="h-[550px]">
          <GeographicForceGraph
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