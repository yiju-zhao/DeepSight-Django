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
import { ChartData } from '../types';

interface DashboardChartsProps {
  data: ChartData;
  isLoading?: boolean;
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#84CC16'];

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

      </div>

      {/* Popular Keywords - Optimized Word Cloud */}
      <div className="bg-white rounded-lg shadow-sm border p-8">
        <h3 className="text-2xl font-semibold text-gray-900 mb-6 text-center">Popular Keywords</h3>
        <div className="flex flex-wrap justify-center items-center gap-2 min-h-[300px] relative">
          {data.top_keywords.slice(0, 30).map((keyword, index) => {
            const maxCount = Math.max(...data.top_keywords.map(k => k.count));
            const minCount = Math.min(...data.top_keywords.map(k => k.count));
            const ratio = (keyword.count - minCount) / (maxCount - minCount || 1);

            // Enhanced font sizing (16px to 48px for better visibility)
            const fontSize = 16 + (ratio * 32);

            // Color selection based on keyword characteristics
            const colorIndex = keyword.name.length % COLORS.length;
            const color = COLORS[colorIndex];

            // Position larger keywords more centrally
            const isLargeKeyword = ratio > 0.6;
            const zIndex = Math.floor(ratio * 10);

            return (
              <span
                key={keyword.name}
                className="inline-block m-1 hover:scale-110 transition-all duration-300 cursor-pointer font-bold"
                style={{
                  fontSize: `${fontSize}px`,
                  color: color,
                  textShadow: '2px 2px 4px rgba(0,0,0,0.1)',
                  zIndex: zIndex,
                  order: isLargeKeyword ? -Math.floor(ratio * 100) : index
                }}
                title={`${keyword.name}: ${keyword.count} publications`}
              >
                {keyword.name}
              </span>
            );
          })}
        </div>
        {data.top_keywords.length === 0 && (
          <div className="text-center text-gray-500 py-12">
            <p>No keywords available for this conference</p>
          </div>
        )}
      </div>
    </div>
  );
}