/**
 * Storybook stories for LoadingSpinner component
 */

import type { Meta, StoryObj } from '@storybook/react';
import LoadingSpinner from './LoadingSpinner';

const meta: Meta<typeof LoadingSpinner> = {
  title: 'UI/LoadingSpinner',
  component: LoadingSpinner,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: 'A customizable loading spinner component for indicating loading states.',
      },
    },
  },
  tags: ['autodocs'],
  argTypes: {
    size: {
      control: { type: 'select' },
      options: ['sm', 'md', 'lg'],
      description: 'The size of the spinner',
    },
    className: {
      control: { type: 'text' },
      description: 'Additional CSS classes',
    },
  },
};

export default meta;
type Story = StoryObj<typeof LoadingSpinner>;

export const Default: Story = {
  args: {},
};

export const Small: Story = {
  args: {
    size: 'sm',
  },
};

export const Medium: Story = {
  args: {
    size: 'md',
  },
};

export const Large: Story = {
  args: {
    size: 'lg',
  },
};

export const CustomColor: Story = {
  args: {
    className: 'text-blue-500',
  },
};

export const InButton: Story = {
  render: () => (
    <button className="inline-flex items-center px-4 py-2 bg-blue-500 text-white rounded-md disabled:opacity-50" disabled>
      <LoadingSpinner size="sm" className="mr-2" />
      Loading...
    </button>
  ),
  parameters: {
    docs: {
      description: {
        story: 'Example of LoadingSpinner used inside a button',
      },
    },
  },
};

export const InCard: Story = {
  render: () => (
    <div className="w-64 h-32 border rounded-lg flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <LoadingSpinner className="mx-auto mb-2" />
        <p className="text-sm text-gray-600">Loading content...</p>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: 'Example of LoadingSpinner used in a card layout',
      },
    },
  },
};