import { BarChart3, TrendingUp, Users, Calendar } from 'lucide-react';
import { useOverview } from '@/features/conference/hooks/useConference';
import { StatCard } from '@/shared/components/ui/stat-card';
import { Button } from '@/shared/components/ui/button';

interface ConferenceSectionProps {
  onNavigateToConferences: () => void;
}

export default function ConferenceSection({ onNavigateToConferences }: ConferenceSectionProps) {
  const { data: overviewData, isLoading } = useOverview();

  return (
    <div className="space-y-4 md:space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        <StatCard
          icon={BarChart3}
          label="Conferences"
          value={overviewData?.total_conferences || 0}
          iconColor="text-gray-700"
          loading={isLoading}
        />
        <StatCard
          icon={TrendingUp}
          label="Publications"
          value={overviewData?.total_papers.toLocaleString() || 0}
          iconColor="text-gray-700"
          loading={isLoading}
        />
        <StatCard
          icon={Calendar}
          label="Years Covered"
          value={overviewData?.years_covered.length || 0}
          iconColor="text-gray-700"
          loading={isLoading}
        />
        <StatCard
          icon={Users}
          label="Avg Papers/Year"
          value={Math.round(overviewData?.avg_papers_per_year || 0)}
          iconColor="text-gray-700"
          loading={isLoading}
        />
      </div>

      {/* CTA Button */}
      <div className="flex justify-center md:justify-start">
        <Button
          variant="accent"
          withArrow
          onClick={onNavigateToConferences}
          disabled={isLoading}
        >
          Explore Conferences
        </Button>
      </div>
    </div>
  );
}
