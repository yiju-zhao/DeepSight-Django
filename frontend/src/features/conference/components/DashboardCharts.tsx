import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line
} from 'recharts';
import { Text } from '@visx/text';
import { scaleLog } from '@visx/scale';
import Wordcloud from '@visx/wordcloud/lib/Wordcloud';
import { ChartData } from '../types';

interface DashboardChartsProps {
  data: ChartData;
  isLoading?: boolean;
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

function WordCloudComponent({ keywords }: WordCloudProps) {
  const words: WordData[] = keywords.map(keyword => ({
    text: keyword.name,
    value: keyword.count,
  }));

  const fontScale = scaleLog({
    domain: [Math.min(...words.map((w) => w.value)), Math.max(...words.map((w) => w.value))],
    range: [12, 60],
  });

  const fontSizeSetter = (datum: WordData) => fontScale(datum.value);

  return (
    <div style={{ width: '100%', height: '320px', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
      <Wordcloud
        words={words}
        width={500}
        height={320}
        fontSize={fontSizeSetter}
        font={'Inter, sans-serif'}
        padding={2}
        spiral="archimedean"
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

export function DashboardCharts({ data, isLoading }: DashboardChartsProps) {
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Geographic Distribution */}
        <ChartCard title="Geographic Distribution">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data.top_countries.slice(0, 8)}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }: any) => `${name} ${((percent as number) * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="count"
              >
                {data.top_countries.slice(0, 8).map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Rating Distribution */}
        <ChartCard title="Rating Distribution">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.ratings_histogram}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="rating" />
              <YAxis />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="count"
                stroke="#F59E0B"
                strokeWidth={2}
                dot={{ fill: '#F59E0B' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Top Organizations */}
        <ChartCard title="Top Organizations">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.top_affiliations.slice(0, 8)} layout="horizontal">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis
                type="category"
                dataKey="name"
                width={120}
                fontSize={11}
              />
              <Tooltip />
              <Bar dataKey="count" fill="#8B5CF6" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Popular Keywords - @visx Word Cloud */}
        <ChartCard title="Popular Keywords">
          {data.top_keywords.length > 0 ? (
            <WordCloudComponent keywords={data.top_keywords.slice(0, 30)} />
          ) : (
            <div className="flex items-center justify-center h-full text-center text-gray-500">
              <p>No keywords available for this conference</p>
            </div>
          )}
        </ChartCard>

      </div>
    </div>
  );
}