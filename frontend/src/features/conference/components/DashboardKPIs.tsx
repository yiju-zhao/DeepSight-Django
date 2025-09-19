import { KPIData } from '../types';
import {
  Users,
  Building2,
  Globe,
  Star,
  Presentation,
  GraduationCap
} from 'lucide-react';

interface DashboardKPIsProps {
  data: KPIData;
  isLoading?: boolean;
}

const KPICard = ({
  icon: Icon,
  label,
  value,
  color,
  isLoading
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  color: string;
  isLoading?: boolean;
}) => {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 bg-gray-200 rounded-lg animate-pulse" />
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-gray-200 rounded animate-pulse w-24" />
            <div className="h-8 bg-gray-200 rounded animate-pulse w-16" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center space-x-4">
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon size={24} className="text-white" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600">{label}</p>
          <p className="text-2xl font-bold text-gray-900">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </p>
        </div>
      </div>
    </div>
  );
};

const MetricCard = ({
  label,
  items,
  isLoading
}: {
  label: string;
  items: { name: string; count: number }[];
  isLoading?: boolean;
}) => {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="h-5 bg-gray-200 rounded animate-pulse w-32 mb-4" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex justify-between items-center">
              <div className="h-4 bg-gray-200 rounded animate-pulse w-20" />
              <div className="h-4 bg-gray-200 rounded animate-pulse w-8" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{label}</h3>
      <div className="space-y-3">
        {items.map(({ name, count }) => (
          <div key={name} className="flex justify-between items-center">
            <span className="text-sm text-gray-600 truncate flex-1 mr-2">{name}</span>
            <span className="text-sm font-semibold text-gray-900 bg-gray-100 px-2 py-1 rounded">
              {count}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export function DashboardKPIs({ data, isLoading }: DashboardKPIsProps) {
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="mb-4">
          <div className="h-7 bg-gray-200 rounded animate-pulse w-64" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <KPICard
              key={i}
              icon={Users}
              label=""
              value=""
              color=""
              isLoading={true}
            />
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <MetricCard label="" items={[]} isLoading={true} />
          <MetricCard label="" items={[]} isLoading={true} />
        </div>
      </div>
    );
  }

  // Process top regions (countries) and organizations (affiliations)
  const topRegions = Object.entries(data.session_distribution || {})
    .sort(([,a], [,b]) => b - a)
    .slice(0, 8); // Show more regions

  const topOrganizations = Object.entries(data.author_position_distribution || {})
    .sort(([,a], [,b]) => b - a)
    .slice(0, 8); // Show more organizations

  return (
    <div className="space-y-6">
      <div className="mb-4">
        <h2 className="text-2xl font-bold text-gray-900">Conference Overview</h2>
      </div>

      {/* Main KPI Cards - 5 cards in one line */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6">
        <KPICard
          icon={Users}
          label="Total Publications"
          value={data.total_publications}
          color="bg-blue-500"
        />

        <KPICard
          icon={GraduationCap}
          label="Unique Authors"
          value={data.unique_authors}
          color="bg-green-500"
        />

        <KPICard
          icon={Building2}
          label="Unique Affiliations"
          value={data.unique_affiliations}
          color="bg-purple-500"
        />

        <KPICard
          icon={Globe}
          label="Unique Countries"
          value={data.unique_countries}
          color="bg-orange-500"
        />

        <KPICard
          icon={Star}
          label="Average Rating"
          value={data.avg_rating.toFixed(1)}
          color="bg-yellow-500"
        />
      </div>

      {/* Additional Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Regions */}
        <MetricCard
          label="Top Regions"
          items={topRegions.map(([region, count]) => ({ name: region, count }))}
        />

        {/* Top Organizations */}
        <MetricCard
          label="Top Organizations"
          items={topOrganizations.map(([org, count]) => ({ name: org, count }))}
        />
      </div>
    </div>
  );
}