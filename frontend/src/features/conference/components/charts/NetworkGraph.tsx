import { memo, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Maximize2, X } from 'lucide-react';
import { ForceGraphData } from '../../types';

interface NetworkGraphProps {
  data: ForceGraphData;
  isLoading?: boolean;
  title: string;
  noDataMessage: string;
  loadingMessage: string;
  themeColor?: 'orange' | 'purple';
}

const NetworkGraphComponent = ({ data, isLoading, title, noDataMessage, loadingMessage, themeColor = 'orange' }: NetworkGraphProps) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Get top 5 nodes by publication count
  const sortedNodes = [...(data?.nodes || [])].sort((a, b) => (b.val || 0) - (a.val || 0));
  const top5NodeIds = new Set(sortedNodes.slice(0, 5).map(n => n.id));

  // Calculate min/max values for normalization
  const linkValues = data?.links?.map(link => link.value || 0) || [];
  const minValue = Math.min(...linkValues);
  const maxValue = Math.max(...linkValues);
  const valueRange = maxValue - minValue;

  // Use normalized value (0-500 range) then square root for both speed and particle count
  const calculateParticleMetrics = (value: number) => {
    if (!value || value <= 0) return { particles: 1, speed: 0.0005 };

    // First normalize to 0-500 range
    const normalizedValue = valueRange === 0 ? 250 : ((value - minValue) / valueRange) * 500;

    // Then apply square root
    const sqrtValue = Math.sqrt(normalizedValue);

    return {
      particles: Math.max(1, Math.round(sqrtValue)), // Round to integer, minimum 1
      speed: Math.max(0.0005, sqrtValue * 0.0002) // Scale speed, minimum for visibility
    };
  };

  // Calculate color based on whether node is in top 5 and theme
  const getNodeColor = (nodeId: string, isTop5: boolean, theme: 'orange' | 'purple') => {
    if (theme === 'orange') {
      return isTop5
        ? 'hsl(25, 85%, 30%)' // Dark orange for top 5
        : 'hsl(25, 85%, 75%)'; // Light orange for rest
    } else {
      return isTop5
        ? 'hsl(260, 85%, 30%)' // Dark purple for top 5
        : 'hsl(260, 85%, 75%)'; // Light purple for rest
    }
  };

  if (isLoading) {
    return (
      <div className="w-full h-[600px] bg-gray-100 rounded-lg animate-pulse flex items-center justify-center">
        <div className="text-gray-500">{loadingMessage}</div>
      </div>
    );
  }

  if (!data?.nodes?.length || !data?.links?.length) {
    return (
      <div className="w-full h-[600px] bg-gray-50 rounded-lg flex items-center justify-center">
        <div className="text-gray-500">{noDataMessage}</div>
      </div>
    );
  }

  const NetworkChart = ({ width, height, fontSize }: {
    width: number;
    height: number;
    fontSize: number;
  }) => (
    <ForceGraph2D
      graphData={data}
      width={width}
      height={height}
      nodeLabel="id"
      nodeAutoColorBy="group"
      linkDirectionalParticles={d => calculateParticleMetrics(d.value || 0).particles}
      linkDirectionalParticleSpeed={d => calculateParticleMetrics(d.value || 0).speed}
      nodeRelSize={0}
      linkWidth={2}
      linkDirectionalParticleWidth={4}
      backgroundColor="#ffffff"
      cooldownTicks={100}
      onEngineStop={() => {}}
      nodeCanvasObject={(node, ctx, globalScale) => {
        const label = node.id;
        const adjustedFontSize = fontSize/globalScale;
        ctx.font = `${adjustedFontSize}px Sans-Serif`;
        const textWidth = ctx.measureText(label).width;
        const bckgDimensions = [textWidth, adjustedFontSize].map(n => n + adjustedFontSize * 0.2);

        if (typeof node.x === 'number' && typeof node.y === 'number' && bckgDimensions.length === 2 && typeof bckgDimensions[0] === 'number' && typeof bckgDimensions[1] === 'number') {
          // Check if this node is in top 5
          const isTop5 = top5NodeIds.has(node.id);

          // Get themed color based on top 5 status
          const nodeColor = getNodeColor(node.id, isTop5, themeColor);

          // Draw background with themed color
          ctx.fillStyle = nodeColor;
          ctx.fillRect(
            node.x - bckgDimensions[0] / 2,
            node.y - bckgDimensions[1] / 2,
            bckgDimensions[0],
            bckgDimensions[1]
          );

          // Draw text - white for dark backgrounds (top 5), black for light backgrounds (rest)
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = isTop5 ? '#ffffff' : '#000000';
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
      d3AlphaDecay={0.02}
      d3VelocityDecay={0.08}
    />
  );

  if (isExpanded) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl w-[95vw] h-[95vh] flex flex-col">
          <div className="flex items-center justify-between p-4 border-b">
            <h3 className="text-xl font-semibold text-gray-900">{title}</h3>
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
        width={550}
        height={550}
        fontSize={12}
      />
    </div>
  );
};

export const NetworkGraph = memo(NetworkGraphComponent);
