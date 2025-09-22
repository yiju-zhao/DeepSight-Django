import { ResponsiveChord } from '@nivo/chord';
import { memo } from 'react';

interface ChordData {
  keys: string[];
  matrix: number[][];
}

interface GeographicChordTop8Props {
  data: ChordData;
  isLoading?: boolean;
}

const GeographicChordTop8 = memo(({ data, isLoading }: GeographicChordTop8Props) => {
  if (isLoading) {
    return (
      <div className="w-full h-96 bg-gray-100 rounded-lg animate-pulse flex items-center justify-center">
        <div className="text-gray-500">Loading geographic collaboration...</div>
      </div>
    );
  }

  if (!data?.keys?.length || !data?.matrix?.length) {
    return (
      <div className="w-full h-96 bg-gray-50 rounded-lg flex items-center justify-center">
        <div className="text-gray-500">No collaboration data available</div>
      </div>
    );
  }

  return (
    <div className="w-full h-96">
      <ResponsiveChord
        data={data.matrix}
        keys={data.keys}
        margin={{ top: 60, right: 60, bottom: 90, left: 60 }}
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
            anchor: 'bottom',
            direction: 'row',
            translateY: 70,
            itemWidth: 80,
            itemHeight: 16,
            itemsSpacing: 0,
            symbolSize: 12,
            symbolShape: 'circle',
            itemDirection: 'left-to-right',
            itemTextColor: '#999',
            effects: [
              {
                on: 'hover',
                style: {
                  itemTextColor: '#000'
                }
              }
            ]
          }
        ]}
      />
    </div>
  );
});

GeographicChordTop8.displayName = 'GeographicChordTop8';

export { GeographicChordTop8 };