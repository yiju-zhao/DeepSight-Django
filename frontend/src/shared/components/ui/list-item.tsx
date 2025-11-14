import * as React from 'react';
import { cn } from '@/shared/utils/utils';

export interface ListItemProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  selected?: boolean;
}

const ListItem = React.forwardRef<HTMLDivElement, ListItemProps>(
  ({ className, title, description, icon, selected = false, onClick, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'p-4 bg-white rounded-lg border transition-all duration-300',
          onClick && 'cursor-pointer',
          selected
            ? 'border-accent-red shadow-huawei-sm'
            : 'border-border hover:shadow-huawei-sm hover:border-gray-300',
          className
        )}
        onClick={onClick}
        {...props}
      >
        <div className="flex items-start space-x-3">
          {icon && (
            <div className="flex-shrink-0 mt-0.5 text-muted-foreground">
              {icon}
            </div>
          )}

          <div className="flex-1 min-w-0">
            <h3 className="text-sm md:text-base font-semibold text-foreground mb-1 line-clamp-2">
              {title}
            </h3>

            {description && (
              <p className="text-xs md:text-sm text-muted-foreground line-clamp-2">
                {description}
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }
);

ListItem.displayName = 'ListItem';

export { ListItem };
