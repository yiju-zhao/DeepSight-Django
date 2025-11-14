import * as React from 'react';
import { cn } from '@/shared/utils/utils';

export interface SectionHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  action?: React.ReactNode;
  withLine?: boolean;
}

const SectionHeader = React.forwardRef<HTMLDivElement, SectionHeaderProps>(
  ({ className, title, action, withLine = true, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn('flex items-center justify-between mb-4 md:mb-6', className)}
        {...props}
      >
        <div className="flex items-center space-x-3 flex-1">
          <h2 className="text-lg md:text-xl font-bold text-foreground tracking-tight">
            {title}
          </h2>
          {withLine && (
            <div className="hidden md:block h-px bg-border flex-1" />
          )}
        </div>

        {action && (
          <div className="ml-4 flex-shrink-0">
            {action}
          </div>
        )}
      </div>
    );
  }
);

SectionHeader.displayName = 'SectionHeader';

export { SectionHeader };
