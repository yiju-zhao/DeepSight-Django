import { KPIData } from '../types';
import {
  Users,
  Building2,
  Globe,
  Star,
  GraduationCap,
  TrendingUp,
  Info,
} from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/shared/components/ui/tooltip';

interface DashboardKPIsProps {
  data: KPIData;
  isLoading?: boolean;
}

interface KPICardProps {
  icon: React.ElementType;
  label: string;
  value: string | number;
  description?: string;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  isLoading?: boolean;
}

const KPICard = ({
  icon: Icon,
  label,
  value,
  description,
  trend,
  isLoading
}: KPICardProps) => {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-[rgba(0,0,0,0.08)_0px_8px_12px] p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1 space-y-3">
            <div className="h-4 bg-[#F5F5F5] rounded animate-pulse w-28" />
            <div className="h-9 bg-[#F5F5F5] rounded animate-pulse w-20" />
          </div>
          <div className="w-12 h-12 bg-[#F5F5F5] rounded-full animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-[rgba(0,0,0,0.08)_0px_8px_12px] hover:shadow-[rgba(0,0,0,0.12)_0px_12px_20px] hover:-translate-y-1 transition-all duration-300 p-6 opacity-0 animate-[slideUp_0.6s_ease-out_forwards]">
      <div className="flex items-start justify-between">
        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-2">
            <p className="text-sm font-normal text-[#666666]">
              {label}
            </p>
            {description && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="h-3.5 w-3.5 text-[#666666]/50 cursor-help" />
                </TooltipTrigger>
                <TooltipContent>{description}</TooltipContent>
              </Tooltip>
            )}
          </div>

          <div className="flex items-baseline gap-3">
            <p className="text-[28px] font-bold text-[#1E1E1E] leading-none">
              {typeof value === 'number' ? value.toLocaleString() : value}
            </p>

            {trend && (
              <div className={`flex items-center gap-1 text-xs font-medium ${
                trend.isPositive ? 'text-green-600' : 'text-red-600'
              }`}>
                <TrendingUp className={`h-3.5 w-3.5 ${!trend.isPositive && 'rotate-180'}`} />
                <span>{Math.abs(trend.value)}%</span>
              </div>
            )}
          </div>
        </div>

        {/* Icon circle - 48px diameter */}
        <div className="w-12 h-12 rounded-full bg-black/5 flex items-center justify-center flex-shrink-0">
          <Icon className="w-5 h-5 text-[#1E1E1E] opacity-80" strokeWidth={2} />
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
      <div className="space-y-8">
        <div className="h-7 bg-[#F5F5F5] rounded animate-pulse w-64" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {Array.from({ length: 5 }).map((_, i) => (
            <KPICard key={i} icon={Users} label="" value="" isLoading={true} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Section Header */}
      <div>
        <h2 className="text-[28px] font-bold text-[#1E1E1E] leading-tight">
          Key Metrics
        </h2>
        <p className="text-sm text-[#666666] mt-2">
          Overview of conference statistics and performance indicators
        </p>
      </div>

      {/* Main KPI Cards - HUAWEI Style 4-column responsive grid with stagger animations */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div style={{ animationDelay: '0ms' }}>
          <KPICard
            icon={Users}
            label="Total Publications"
            value={data.total_publications}
            description="Total number of publications in this conference"
          />
        </div>

        <div style={{ animationDelay: '200ms' }}>
          <KPICard
            icon={GraduationCap}
            label="Authors"
            value={data.unique_authors}
            description="Unique authors who contributed to publications"
          />
        </div>

        <div style={{ animationDelay: '400ms' }}>
          <KPICard
            icon={Building2}
            label="Organizations"
            value={data.unique_affiliations}
            description="Unique organizations represented in publications"
          />
        </div>

        <div style={{ animationDelay: '600ms' }}>
          <KPICard
            icon={Globe}
            label="Countries"
            value={data.unique_countries}
            description="Countries represented in author affiliations"
          />
        </div>

        <div style={{ animationDelay: '800ms' }}>
          <KPICard
            icon={Star}
            label="Average Rating"
            value={data.avg_rating.toFixed(1)}
            description="Average quality rating of all publications"
          />
        </div>
      </div>
    </div>
  );
}
