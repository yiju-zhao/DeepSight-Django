import { memo, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import ForceGraph3D from 'react-force-graph-3d';
import SpriteText from 'three-spritetext';
import { Maximize2, X } from 'lucide-react';
import { ForceGraphData } from '../../types';

interface NetworkGraphProps {
  data: ForceGraphData;
  isLoading?: boolean;
  title: string;
  noDataMessage: string;
  loadingMessage: string;
  use3D?: boolean;
}

const NetworkGraphComponent = ({ data, isLoading, title, noDataMessage, loadingMessage, use3D = false }: NetworkGraphProps) => {
  const [isExpanded, setIsExpanded] = useState(false);

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
  }) => {
    if (use3D) {
      return (
        <ForceGraph3D
          graphData={data}
          width={width}
          height={height}
          nodeAutoColorBy="group"
          nodeThreeObjectExtend={true}
          nodeThreeObject={(node: any) => {
            const sprite = new SpriteText(node.id);
            sprite.color = node.color || '#333';
            sprite.textHeight = 8;
            return sprite;
          }}
          linkDirectionalParticles="value"
          linkDirectionalParticleSpeed={(d: any) => d.value * 0.001}
          linkWidth={2}
          linkDirectionalParticleWidth={4}
          backgroundColor="#ffffff"
          cooldownTicks={100}
          onEngineStop={() => {}}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.08}
        />
      );
    }

    return (
      <ForceGraph2D
        graphData={data}
        width={width}
        height={height}
        nodeLabel="id"
        nodeAutoColorBy="group"
        linkDirectionalParticles="value"
        linkDirectionalParticleSpeed={(d: any) => d.value * 0.001}
        nodeRelSize={0}
        linkWidth={2}
        linkDirectionalParticleWidth={4}
        backgroundColor="#ffffff"
        cooldownTicks={100}
        onEngineStop={() => {}}
        nodeCanvasObject={(node: any, ctx: any, globalScale: number) => {
          const label = node.id;
          const adjustedFontSize = fontSize/globalScale;
          ctx.font = `${adjustedFontSize}px Sans-Serif`;
          const textWidth = ctx.measureText(label).width;
          const bckgDimensions = [textWidth, adjustedFontSize].map((n: number) => n + adjustedFontSize * 0.2);

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
        nodePointerAreaPaint={(node: any, color: any, ctx: any) => {
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
  };

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
