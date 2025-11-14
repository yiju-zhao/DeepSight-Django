import { cn } from "@/shared/utils/utils";
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import React from 'react';

const buttonVariants = cva(
	'inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
	{
		variants: {
			variant: {
				default: 'bg-primary text-primary-foreground hover:bg-primary/90',
				destructive:
          'bg-destructive text-destructive-foreground hover:bg-destructive/90',
				outline:
          'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
				secondary:
          'bg-secondary text-secondary-foreground hover:bg-secondary/80',
				ghost: 'hover:bg-accent hover:text-accent-foreground',
				link: 'text-primary underline-offset-4 hover:underline',
				accent: 'bg-accent-red text-white hover:bg-accent-red-hover transition-all duration-300',
			},
			size: {
				default: 'h-10 px-4 py-2',
				sm: 'h-9 rounded-md px-3',
				lg: 'h-11 rounded-md px-8',
				icon: 'h-10 w-10',
			},
		},
		defaultVariants: {
			variant: 'default',
			size: 'default',
		},
	},
);

export interface ButtonProps
	extends React.ButtonHTMLAttributes<HTMLButtonElement>,
		VariantProps<typeof buttonVariants> {
	asChild?: boolean;
	withArrow?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
	({ className, variant, size, asChild = false, withArrow = false, children, ...props }, ref) => {
		const Comp = asChild ? Slot : 'button';
		return (
			<Comp
				className={cn(
					buttonVariants({ variant, size }),
					withArrow && 'group relative pr-10',
					className
				)}
				ref={ref}
				{...props}
			>
				{children}
				{withArrow && (
					<span className="absolute right-3 top-1/2 -translate-y-1/2 transition-transform duration-600 ease-out group-hover:translate-x-1">
						<svg
							width="6"
							height="6"
							viewBox="0 0 6 6"
							fill="none"
							xmlns="http://www.w3.org/2000/svg"
							className="rotate-45"
						>
							<path
								d="M0 0 L6 0 L6 6"
								stroke="currentColor"
								strokeWidth="2"
							/>
						</svg>
					</span>
				)}
			</Comp>
		);
	}
);
Button.displayName = 'Button';

export { Button, buttonVariants };
