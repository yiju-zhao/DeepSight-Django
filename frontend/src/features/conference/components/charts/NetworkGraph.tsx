import { memo, useState, useEffect, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Maximize2, X } from 'lucide-react';
import { ForceGraphData } from '../../types';

interface NetworkGraphProps {
  data: ForceGraphData;
  isLoading?: boolean;
  title: string;
  noDataMessage: string;
  loadingMessage: string;
  themeColor?: 'orange' | 'purple'; // Deprecated but kept for interface compat for now
}

const NetworkGraphComponent = ({ data, isLoading, title, noDataMessage, loadingMessage }: NetworkGraphProps) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [dimensions, setDimensions] = useState<{ width: number; height: number }>({
    width: 0,
    height: 0,
  });

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver(entries => {
      if (!entries[0]) return;
      const { width, height } = entries[0].contentRect;
      setDimensions({ width, height });
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const sortedNodes = [...(data?.nodes || [])].sort((a, b) => (b.val || 0) - (a.val || 0));
  const top10NodeIds = new Set(sortedNodes.slice(0, 10).map(n => n.id));

  // Particle logic
  const linkValues = data?.links?.map(link => link.value || 0) || [];
  const minVal = Math.min(...linkValues);
  const maxVal = Math.max(...linkValues);
  const valRange = maxVal - minVal;

  const normalizeParticles = (value: number) => {
    if (valRange === 0) return { particles: 1, speed: 0.002 };
    const norm = (value - minVal) / valRange;
    const scaled = Math.round(norm * 10); // fewer particles for cleaner look
    return {
      particles: Math.max(0, scaled),
      speed: Math.max(0.001, scaled * 0.0005)
    };
  };

  const getNodeColor = (nodeId: string, isTop10: boolean) => {
    // Top nodes get Huawei Red, others get Black/Dark Gray
    if (isTop10) return '#CE0E2D';
    return '#000000';
  };

  if (isLoading) {
    return (
      <div className="w-full h-[600px] bg-[#FAFAFA] rounded-lg animate-pulse flex items-center justify-center border border-[#E3E3E3]">
        <div className="text-[#999999]">{loadingMessage}</div>
      </div>
    );
  }

  if (!data?.nodes?.length || !data?.links?.length) {
    return (
      <div className="w-full h-[600px] bg-[#FAFAFA] rounded-lg flex items-center justify-center border border-dashed border-[#E3E3E3]">
        <div className="text-[#999999]">{noDataMessage}</div>
      </div>
    );
  }

  const NetworkChart = ({ width, height, fontSize }: { width: number; height: number; fontSize: number }) => (
    <ForceGraph2D
      graphData={data}
      width={width}
      height={height}
      nodeLabel="id"
      nodeAutoColorBy="group"
      linkDirectionalParticles={d => normalizeParticles(d.value || 0).particles}
      linkDirectionalParticleSpeed={d => normalizeParticles(d.value || 0).speed}
      linkDirectionalParticleColor={() => '#CE0E2D'}
      nodeRelSize={6}
      linkWidth={1}
      linkColor={() => '#E3E3E3'} // Light gray links
      backgroundColor="#ffffff"
      cooldownTicks={100}
      nodeCanvasObject={(node, ctx, globalScale) => {
        const label = node.id;
        const adjustedFontSize = fontSize / globalScale;
        ctx.font = `600 ${adjustedFontSize}px Open Sans, sans-serif`;
        const textWidth = ctx.measureText(label).width;
        const bckgDimensions = [textWidth, adjustedFontSize].map(n => n + adjustedFontSize * 0.4);

        if (typeof node.x === 'number' && typeof node.y === 'number') {
          const isTop10 = top10NodeIds.has(node.id);
          const nodeColor = getNodeColor(node.id, isTop10);

          // Draw node circle (instead of rectangular background)
          ctx.beginPath();
          ctx.arc(node.x, node.y, 4, 0, 2 * Math.PI, false);
          ctx.fillStyle = nodeColor;
          ctx.fill();

          // Draw minimal background for text clarity
          ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
          ctx.fillRect(
            node.x - (bckgDimensions[0] ?? 0) / 2,
            node.y - (bckgDimensions[1] ?? 0) / 2,
            bckgDimensions[0] ?? 0,
            bckgDimensions[1] ?? 0
          );

          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = nodeColor; // Text color matches node importance
          ctx.fillText(label, node.x, node.y);

          (node as any).__bckgDimensions = bckgDimensions;
        }
      }}
    />
  );

  if (isExpanded) {
    return (
      <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 backdrop-blur-sm">
        <div className="bg-white rounded-lg shadow-2xl w-[95vw] h-[95vh] flex flex-col overflow-hidden">
          <div className="flex items-center justify-between p-4 border-b border-[#E3E3E3]">
            <h3 className="text-xl font-bold text-[#1E1E1E]">{title}</h3>
            <button
              onClick={() => setIsExpanded(false)}
              className="p-2 hover:bg-[#F5F5F5] rounded-full transition-colors"
            >
              <X className="w-6 h-6 text-[#666666]" />
            </button>
          </div>
          <div className="flex-1 flex items-center justify-center bg-white">
            <NetworkChart
              width={window.innerWidth * 0.9}
              height={window.innerHeight * 0.8}
              fontSize={14}
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative w-full h-full flex items-center justify-center group">
      <button
        onClick={() => setIsExpanded(true)}
        className="absolute top-2 right-2 p-2 bg-white/80 hover:bg-white rounded-lg shadow-sm border border-[#E3E3E3] transition-all opacity-0 group-hover:opacity-100 z-10"
        title="Expand to full screen"
      >
        <Maximize2 className="w-5 h-5 text-[#666666]" />
      </button>
      {dimensions.width > 0 && dimensions.height > 0 && (
        <NetworkChart
          width={Math.floor(dimensions.width)}
          height={Math.floor(dimensions.height)}
          fontSize={10}
        />
      )}
    </div>
  );
};

export const NetworkGraph = memo(NetworkGraphComponent);
