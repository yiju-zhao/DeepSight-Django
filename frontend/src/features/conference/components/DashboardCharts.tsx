import { Text } from '@visx/text';
import { scaleLog } from '@visx/scale';
import Wordcloud from '@visx/wordcloud/lib/Wordcloud';
import { ChartData } from '../types';
import { GeographicChordTop8 } from './GeographicChordTop8';
import { TopOrgChordTop10 } from './TopOrgChordTop10';
import { RatingHistogramFine } from './RatingHistogramFine';
import { memo, useState, useCallback } from 'react';

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

function getRotationDegree() {
  const rand = Math.random();
  const degree = rand > 0.5 ? 60 : -60;
  return rand * degree;
}

const fixedValueGenerator = () => 0.5;

interface WordCloudProps {
  keywords: Array<{ name: string; count: number }>;
}

type SpiralType = 'archimedean' | 'rectangular';

function WordCloudComponent({ keywords }: WordCloudProps) {
  const [spiralType, setSpiralType] = useState<SpiralType>('rectangular');
  const [withRotation, setWithRotation] = useState(false);

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
    <div className="w-full">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <label className="flex items-center text-sm">
            <span className="mr-2">Spiral:</span>
            <select
              onChange={(e) => setSpiralType(e.target.value as SpiralType)}
              value={spiralType}
              className="px-2 py-1 border border-gray-300 rounded text-sm"
            >
              <option value="archimedean">Archimedean</option>
              <option value="rectangular">Rectangular</option>
            </select>
          </label>
          <label className="flex items-center text-sm">
            <input
              type="checkbox"
              checked={withRotation}
              onChange={() => setWithRotation(!withRotation)}
              className="mr-2"
            />
            Rotation
          </label>
        </div>
      </div>
      <div style={{ width: '100%', height: '320px', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <Wordcloud
          words={words}
          width={500}
          height={320}
          fontSize={fontSizeSetter}
          font={'Inter, sans-serif'}
          padding={2}
          spiral={spiralType}
          rotate={withRotation ? getRotationDegree : 0}
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
    </div>
  );
}

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
    </div>
  );
};

DashboardChartsComponent.displayName = 'DashboardCharts';

export const DashboardCharts = memo(DashboardChartsComponent);