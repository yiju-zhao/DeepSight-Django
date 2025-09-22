import { ResponsiveTreeMap } from '@nivo/treemap';
import { memo } from 'react';

interface TreemapData {
  name: string;
  value: number;
}

interface KeywordsTreemapProps {
  data: TreemapData[];
  isLoading?: boolean;
}

const KeywordsTreemap = memo(({ data, isLoading }: KeywordsTreemapProps) => {
  if (isLoading) {
    return (
      <div className="w-full h-96 bg-gray-100 rounded-lg animate-pulse flex items-center justify-center">
        <div className="text-gray-500">Loading keywords...</div>
      </div>
    );
  }

  if (!data?.length) {
    return (
      <div className="w-full h-96 bg-gray-50 rounded-lg flex items-center justify-center">
        <div className="text-gray-500">No keyword data available</div>
      </div>
    );
  }

  // Transform data for TreeMap - it expects a nested structure
  const treemapData = {
    name: 'keywords',
    children: data.map(item => ({
      name: item.name,
      value: item.value,
      id: item.name
    }))
  };

  return (
    <div className="w-full h-96">
      <ResponsiveTreeMap
        data={treemapData}
        identity="name"
        value="value"
        valueFormat=".0f"
        margin={{ top: 10, right: 10, bottom: 10, left: 10 }}
        labelSkipSize={10}
        labelTextColor={{
          from: 'color',
          modifiers: [['darker', 1.2]]
        }}
        parentLabelPosition="left"
        parentLabelTextColor={{
          from: 'color',
          modifiers: [['darker', 2]]
        }}
        borderColor={{
          from: 'color',
          modifiers: [['darker', 0.1]]
        }}
        colors={{ scheme: 'spectral' }}
        nodeOpacity={0.8}
        animate={true}
        motionConfig="gentle"
        tooltip={({ node }) => (
          <div className="bg-white p-3 shadow-lg rounded-lg border">
            <div className="font-semibold text-gray-900">
              {node.data.name}
            </div>
            <div className="text-sm text-gray-600">
              {node.value} publications
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {((node.value / treemapData.children.reduce((sum, item) => sum + item.value, 0)) * 100).toFixed(1)}% of keywords
            </div>
          </div>
        )}
        labelFormat={(value: any) => {
          // Only show labels for larger rectangles to avoid clutter
          if (typeof value === 'string') {
            return value.length > 10 ? `${value.substring(0, 10)}...` : value;
          }
          return String(value);
        }}
      />
    </div>
  );
});

KeywordsTreemap.displayName = 'KeywordsTreemap';

export { KeywordsTreemap };