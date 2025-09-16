/**
 * Storybook stories for Badge component
 */

import type { Meta, StoryObj } from '@storybook/react';
import { Badge } from './badge';
import { CheckCircle, AlertCircle, Clock, Star } from 'lucide-react';

const meta: Meta<typeof Badge> = {
  title: 'UI/Badge',
  component: Badge,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: 'A small status indicator component for labels, statuses, and categories.',
      },
    },
  },
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: { type: 'select' },
      options: ['default', 'secondary', 'destructive', 'outline'],
      description: 'The visual variant of the badge',
    },
  },
};

export default meta;
type Story = StoryObj<typeof Badge>;

export const Default: Story = {
  args: {
    children: 'Default',
  },
};

export const Secondary: Story = {
  args: {
    variant: 'secondary',
    children: 'Secondary',
  },
};

export const Destructive: Story = {
  args: {
    variant: 'destructive',
    children: 'Destructive',
  },
};

export const Outline: Story = {
  args: {
    variant: 'outline',
    children: 'Outline',
  },
};

// Status badges
export const StatusCompleted: Story = {
  args: {
    variant: 'default',
    className: 'bg-green-500 hover:bg-green-600',
    children: (
      <>
        <CheckCircle className="w-3 h-3 mr-1" />
        Completed
      </>
    ),
  },
};

export const StatusPending: Story = {
  args: {
    variant: 'secondary',
    className: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200',
    children: (
      <>
        <Clock className="w-3 h-3 mr-1" />
        Pending
      </>
    ),
  },
};

export const StatusFailed: Story = {
  args: {
    variant: 'destructive',
    children: (
      <>
        <AlertCircle className="w-3 h-3 mr-1" />
        Failed
      </>
    ),
  },
};

// Category badges
export const Category: Story = {
  args: {
    variant: 'outline',
    children: 'Technology',
  },
};

export const Priority: Story = {
  args: {
    className: 'bg-orange-100 text-orange-800 border-orange-200 hover:bg-orange-200',
    children: (
      <>
        <Star className="w-3 h-3 mr-1" />
        High Priority
      </>
    ),
  },
};

// Number badges
export const Count: Story = {
  args: {
    variant: 'secondary',
    children: '42',
  },
};

export const NewItems: Story = {
  args: {
    className: 'bg-red-500 text-white hover:bg-red-600',
    children: '3',
  },
};

// Size variations
export const Small: Story = {
  args: {
    className: 'text-xs px-2 py-0.5',
    children: 'Small',
  },
};

export const Large: Story = {
  args: {
    className: 'text-sm px-3 py-1',
    children: 'Large',
  },
};

// Multiple badges example
export const MultipleBadges: Story = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <Badge>React</Badge>
      <Badge variant="secondary">TypeScript</Badge>
      <Badge variant="outline">Storybook</Badge>
      <Badge variant="destructive">Bug</Badge>
      <Badge className="bg-green-500 hover:bg-green-600">
        <CheckCircle className="w-3 h-3 mr-1" />
        Ready
      </Badge>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: 'Example showing multiple badges used together.',
      },
    },
  },
};