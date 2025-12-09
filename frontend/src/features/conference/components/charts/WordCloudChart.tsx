import { Text } from '@visx/text';
import { scaleLog } from '@visx/scale';
import Wordcloud from '@visx/wordcloud/lib/Wordcloud';

// Colorful Palette for Word Cloud
const COLORS = [
  '#00429d', '#4771b2', '#73a2c6', '#a5d5d8', '#ffffe0', '#ffbcaf', '#ff988c', '#ff595e', '#ff0033'
];

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
      <div className="w-full h-80 bg-[#FAFAFA] rounded-lg flex items-center justify-center border border-dashed border-[#E3E3E3]">
        <div className="text-[#999999]">No keyword data available</div>
      </div>
    );
  }

  const fontScale = scaleLog({
    domain: [Math.min(...words.map((w) => w.value)), Math.max(...words.map((w) => w.value))],
    range: [14, 64], // Slightly larger minimum font size for readability
  });

  const fontSizeSetter = (datum: { text: string; value: number }) => fontScale(datum.value);

  return (
    <div className="w-full flex justify-center items-center h-80">
      <Wordcloud
        words={words}
        width={500}
        height={320}
        fontSize={fontSizeSetter}
        font={"'Open Sans', 'Microsoft YaHei', sans-serif"}
        padding={4}
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
              className="cursor-pointer hover:opacity-70 transition-opacity duration-200"
              style={{
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
