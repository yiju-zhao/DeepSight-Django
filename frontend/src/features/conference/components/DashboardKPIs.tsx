import { memo } from 'react';
import { Users, FileText, Building2, Globe, Star, TrendingUp, TrendingDown } from 'lucide-react';
import { KPIData } from '../types';

interface DashboardKPIsProps {
  data: KPIData;
  isLoading?: boolean;
}

const KPICard = ({
  title,
  value,
  icon: Icon,
  trend,
  trendValue,
  delay = 0
}: {
  title: string;
  value: string | number;
  icon: any;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  delay?: number;
}) => (
  <div
    className="bg-white rounded-lg p-6 border border-[#E3E3E3] shadow-[rgba(0,0,0,0.08)_0px_8px_12px] hover:shadow-[rgba(0,0,0,0.12)_0px_12px_20px] transition-all duration-300"
    style={{ animationDelay: `${delay}ms` }}
  >
    <div className="flex items-start justify-between mb-4">
      <div>
        <p className="text-sm font-medium text-[#666666] uppercase tracking-wide">{title}</p>
        <h3 className="text-3xl font-bold text-[#1E1E1E] mt-1 tracking-tight">{value}</h3>
      </div>
      <div className="p-2 bg-[#F5F5F5] rounded-full">
        <Icon className="w-5 h-5 text-[#1E1E1E]" />
      </div>
    </div>

    {trend && trendValue && (
      <div className="flex items-center text-xs font-medium">
        {trend === 'up' ? (
          <TrendingUp className="w-3.5 h-3.5 mr-1 text-[#CE0E2D]" />
        ) : trend === 'down' ? (
          <TrendingDown className="w-3.5 h-3.5 mr-1 text-[#666666]" />
        ) : null}
        <span
          className={
            trend === 'up' ? 'text-[#CE0E2D]' : 'text-[#666666]'
          }
        >
          {trendValue}
        </span>
        <span className="text-[#999999] ml-1">vs last year</span>
      </div>
    )}
  </div>
);

const DashboardKPIsComponent = ({ data, isLoading }: DashboardKPIsProps) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="bg-white h-32 rounded-lg shadow-sm border border-gray-100 p-6 animate-pulse">
            <div className="flex justify-between items-start">
              <div className="space-y-3">
                <div className="h-4 w-24 bg-gray-100 rounded" />
                <div className="h-8 w-16 bg-gray-100 rounded" />
              </div>
              <div className="h-10 w-10 bg-gray-100 rounded-full" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  const kpis = [
    {
      title: 'Total Publications',
      value: data.total_publications.toLocaleString(),
      icon: FileText,
      trend: 'up' as const, // Mock trend for visualization
      trendValue: '+12.5%',
    },
    {
      title: 'Unique Authors',
      value: data.unique_authors.toLocaleString(),
      icon: Users,
      trend: 'up' as const,
      trendValue: '+8.2%',
    },
    {
      title: 'Organizations',
      value: data.unique_affiliations.toLocaleString(),
      icon: Building2,
      trend: 'neutral' as const,
      trendValue: '0%',
    },
    {
      title: 'Countries',
      value: data.unique_countries.toLocaleString(),
      icon: Globe,
      trend: 'up' as const,
      trendValue: '+2',
    },
    {
      title: 'Avg Rating',
      value: Number(data.avg_rating).toFixed(2),
      icon: Star,
      trend: 'up' as const,
      trendValue: '+0.4',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
      {kpis.map((kpi, index) => (
        <KPICard
          key={kpi.title}
          {...kpi}
          delay={index * 100}
        />
      ))}
    </div>
  );
};

export const DashboardKPIs = memo(DashboardKPIsComponent);
