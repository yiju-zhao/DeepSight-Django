/**
 * Redesigned Dashboard Page
 * Features a modern, clean layout with three main overview sections:
 * 1. Conference Overview
 * 2. Intelligence Reports
 * 3. AI Podcasts
 */

import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, FileText, Mic, ArrowRight, Sparkles } from 'lucide-react';
import Header from '@/shared/components/layout/Header';
import Footer from '@/shared/components/layout/Footer';
import { useDashboardData } from '../queries';
import { useOverview } from '@/features/conference/hooks/useConference';
import LoadingState from '../components/LoadingState';
import { Button } from '@/shared/components/ui/button';
import { cn } from '@/shared/utils/utils';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { reports, podcasts, loading: dashboardLoading } = useDashboardData();
  const { data: conferenceData, isLoading: conferenceLoading } = useOverview();

  const isLoading = dashboardLoading || conferenceLoading;

  const handleNavigate = useCallback((path: string) => {
    navigate(path);
  }, [navigate]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Header />
        <main className="flex-grow pt-[var(--header-height)] flex items-center justify-center">
          <LoadingState />
        </main>

      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />

      <main className="flex-grow pt-[var(--header-height)]">
        {/* Modern Page Header */}
        <section className="relative bg-white border-b border-gray-100">
          <div className="absolute inset-0 bg-gradient-to-b from-gray-50/50 to-white/20 pointer-events-none" />
          <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-16 relative z-10">
            <div className="max-w-3xl">
              <div className="flex items-center gap-2 mb-4">
                <span className="px-3 py-1 rounded-full bg-black/5 text-xs font-medium text-gray-600 flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  Research Hub
                </span>
              </div>
              <h1 className="text-4xl md:text-5xl font-bold text-[#1E1E1E] tracking-tight mb-4">
                Dashboard
              </h1>
              <p className="text-lg text-gray-500 leading-relaxed">
                Welcome to your central intelligence hub. Access conferences, analyze reports, and listen to AI insights.
              </p>
            </div>
          </div>
        </section>

        {/* Main Content Grid */}
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">

            {/* Conference Card */}
            <DashboardCard
              title="Conferences"
              description="Explore academic gatherings and publications."
              icon={<Users className="w-6 h-6 text-white" />}
              iconBg="bg-blue-600"
              stats={[
                { label: 'Total Conferences', value: conferenceData?.total_conferences || 0 },
                { label: 'Publications', value: conferenceData?.total_papers.toLocaleString() || 0 },
              ]}
              onClick={() => handleNavigate('/conference')}
              actionLabel="Enter Conference Hub"
            />

            {/* Reports Card */}
            <DashboardCard
              title="Intelligence Reports"
              description="Deep dive into generated research reports."
              icon={<FileText className="w-6 h-6 text-white" />}
              iconBg="bg-emerald-600"
              stats={[
                { label: 'Total Reports', value: reports.length },
                { label: 'Latest', value: reports[0]?.title || reports[0]?.article_title || 'No reports yet', isText: true },
              ]}
              onClick={() => handleNavigate('/report')}
              actionLabel="View Reports"
            />

            {/* Podcast Card */}
            <DashboardCard
              title="AI Podcasts"
              description="Listen to curated AI-generated discussions."
              icon={<Mic className="w-6 h-6 text-white" />}
              iconBg="bg-violet-600"
              stats={[
                { label: 'Total Podcasts', value: podcasts.length },
                { label: 'Latest', value: podcasts[0]?.title || 'No podcasts yet', isText: true },
              ]}
              onClick={() => handleNavigate('/podcast')}
              actionLabel="Listen to Podcasts"
            />

          </div>
        </div>
      </main>


    </div>
  );
}

interface DashboardCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  iconBg: string;
  stats: { label: string; value: string | number; isText?: boolean }[];
  onClick: () => void;
  actionLabel: string;
}

function DashboardCard({ title, description, icon, iconBg, stats, onClick, actionLabel }: DashboardCardProps) {
  return (
    <div
      className="group relative bg-white rounded-2xl border border-gray-100 p-8 shadow-sm hover:shadow-huawei-md transition-all duration-300 flex flex-col h-full cursor-pointer overflow-hidden"
      onClick={onClick}
    >
      {/* Hover Gradient Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-gray-50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

      <div className="relative z-10 flex flex-col h-full">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center shadow-sm", iconBg)}>
            {icon}
          </div>
          <div className="w-8 h-8 rounded-full bg-gray-50 flex items-center justify-center group-hover:bg-black group-hover:text-white transition-colors duration-300">
            <ArrowRight className="w-4 h-4" />
          </div>
        </div>

        {/* Content */}
        <div className="mb-8">
          <h3 className="text-xl font-bold text-gray-900 mb-2 group-hover:text-black transition-colors">
            {title}
          </h3>
          <p className="text-gray-500 text-sm leading-relaxed">
            {description}
          </p>
        </div>

        {/* Stats */}
        <div className="mt-auto space-y-4 mb-8">
          {stats.map((stat, index) => (
            <div key={index} className="flex items-center justify-between text-sm">
              <span className="text-gray-500">{stat.label}</span>
              <span className={cn("font-medium text-gray-900", stat.isText && "truncate max-w-[150px]")}>
                {stat.value}
              </span>
            </div>
          ))}
        </div>

        {/* Action Button (Visual only, whole card is clickable) */}
        <div className="mt-auto pt-6 border-t border-gray-100">
          <span className="text-sm font-semibold text-gray-900 flex items-center gap-2 group-hover:gap-3 transition-all">
            {actionLabel}
            <ArrowRight className="w-4 h-4" />
          </span>
        </div>
      </div>
    </div>
  );
}
