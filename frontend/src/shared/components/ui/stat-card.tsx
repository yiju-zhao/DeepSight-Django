import * as React from 'react';
import { cn } from '@/shared/utils/utils';
import { LucideIcon } from 'lucide-react';

export interface StatCardProps extends React.HTMLAttributes<HTMLDivElement> {
  icon: LucideIcon;
  label: string;
  value: string | number;
  iconColor?: string;
  loading?: boolean;
}

const StatCard = React.forwardRef<HTMLDivElement, StatCardProps>(
  ({ className, icon: Icon, label, value, iconColor = 'text-gray-600', loading = false, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'flex flex-col items-center justify-center p-6 bg-white rounded-lg border border-border',
          'transition-all duration-300',
          'hover:shadow-huawei-sm hover:-translate-y-0.5',
          className
        )}
        {...props}
      >
        <div className={cn('mb-3', iconColor)}>
          <Icon className="w-8 h-8 md:w-10 md:h-10" />
        </div>

        {loading ? (
          <>
            <div className="h-8 w-20 bg-gray-200 animate-pulse rounded mb-2" />
            <div className="h-4 w-24 bg-gray-200 animate-pulse rounded" />
          </>
        ) : (
          <>
            <div className="text-2xl md:text-3xl font-bold text-foreground mb-1">
              {value}
            </div>
            <div className="text-sm md:text-base text-muted-foreground font-medium text-center">
              {label}
            </div>
          </>
        )}
      </div>
    );
  }
);

StatCard.displayName = 'StatCard';

export { StatCard };
