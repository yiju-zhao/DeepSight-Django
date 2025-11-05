import { Text } from '@visx/text';
import { scaleLog } from '@visx/scale';
import Wordcloud from '@visx/wordcloud/lib/Wordcloud';

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#84CC16'];
const fixedValueGenerator = () => 0.5;

interface WordCloudChartProps {
  keywords: Array<{ name: string; count: number }>;
}

export function WordCloudChart({ keywords }: WordCloudChartProps) {
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
        font={"'Open Sans', 'Microsoft YaHei', '微软雅黑', 'PingFang SC', 'Hiragino Sans GB', 'Heiti SC', 'Helvetica Neue', 'Arial', 'sans-serif'"}
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
