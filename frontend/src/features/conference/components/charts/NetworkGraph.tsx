import { memo, useState } from 'react';
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
}

const NetworkGraphComponent = ({ data, isLoading, title, noDataMessage, loadingMessage }: NetworkGraphProps) => {
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
  }) => (
    <ForceGraph3D
      graphData={data}
      width={width}
      height={height}
      nodeLabel={(node: any) => `<div><b>${node.entity || node.id}</b></div>`}
      nodeAutoColorBy="entity"
      nodeThreeObjectExtend={true}
      nodeThreeObject={(node: any) => {
        const sprite = new SpriteText(node.entity || node.id);
        sprite.color = node.color;
        sprite.textHeight = fontSize * 0.6;
        return sprite;
      }}
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
