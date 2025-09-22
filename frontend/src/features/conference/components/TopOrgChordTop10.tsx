import { ResponsiveChord } from '@nivo/chord';
import { memo } from 'react';

interface ChordData {
  keys: string[];
  matrix: number[][];
}

interface TopOrgChordTop10Props {
  data: ChordData;
  isLoading?: boolean;
}

const TopOrgChordTop10 = memo(({ data, isLoading }: TopOrgChordTop10Props) => {
  if (isLoading) {
    return (
      <div className="w-full h-96 bg-gray-100 rounded-lg animate-pulse flex items-center justify-center">
        <div className="text-gray-500">Loading organization collaboration...</div>
      </div>
    );
  }

  if (!data?.keys?.length || !data?.matrix?.length) {
    return (
      <div className="w-full h-96 bg-gray-50 rounded-lg flex items-center justify-center">
        <div className="text-gray-500">No organization collaboration data available</div>
      </div>
    );
  }

  return (
    <div className="w-full h-96">
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
            anchor: 'bottom',
            direction: 'row',
            translateY: 70,
            itemWidth: 70,
            itemHeight: 14,
            itemsSpacing: 0,
            symbolSize: 10,
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

TopOrgChordTop10.displayName = 'TopOrgChordTop10';

export { TopOrgChordTop10 };