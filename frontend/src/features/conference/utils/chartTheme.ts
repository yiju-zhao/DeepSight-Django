/**
 * Chart Theme Configuration
 *
 * Unified theme system for all Nivo charts in the conference dashboard.
 * Provides consistent colors, typography, and styling across visualizations.
 *
 * Design Philosophy:
 * - Modern and professional color palette
 * - Accessibility-first (WCAG AA compliant)
 * - Harmonious with shadcn/ui design system
 * - Optimized for both light and dark modes
 */

import { Theme } from '@nivo/core';

// ============================================================================
// COLOR PALETTE
// ============================================================================

/**
 * Primary chart colors - carefully selected for visual harmony and distinction
 * Based on HSL color space for better perceptual uniformity
 */
export const chartColors = [
  'hsl(221, 83%, 53%)',   // Blue - Primary brand color
  'hsl(262, 83%, 58%)',   // Purple - Secondary accent
  'hsl(142, 76%, 36%)',   // Green - Success/positive
  'hsl(24, 94%, 50%)',    // Orange - Warning/highlight
  'hsl(340, 82%, 52%)',   // Pink - Accent
  'hsl(199, 89%, 48%)',   // Cyan - Info
  'hsl(45, 93%, 47%)',    // Yellow - Alert
  'hsl(168, 76%, 36%)',   // Teal - Neutral accent
  'hsl(280, 67%, 50%)',   // Violet - Deep accent
  'hsl(14, 90%, 53%)',    // Red-Orange - Strong highlight
];

/**
 * Semantic color mapping for specific data types
 */
export const semanticColors = {
  primary: 'hsl(221, 83%, 53%)',
  success: 'hsl(142, 76%, 36%)',
  warning: 'hsl(38, 92%, 50%)',
  error: 'hsl(0, 84%, 60%)',
  info: 'hsl(199, 89%, 48%)',
  neutral: 'hsl(215, 16%, 47%)',
};

/**
 * Gradient definitions for enhanced visual appeal
 */
export const chartGradients = {
  primary: {
    from: 'hsl(221, 83%, 53%)',
    to: 'hsl(221, 83%, 43%)',
  },
  success: {
    from: 'hsl(142, 76%, 36%)',
    to: 'hsl(142, 76%, 26%)',
  },
  multi: [
    'hsl(221, 83%, 53%)',
    'hsl(262, 83%, 58%)',
    'hsl(142, 76%, 36%)',
  ],
};

// ============================================================================
// NIVO THEME CONFIGURATION
// ============================================================================

/**
 * Base Nivo theme configuration
 * Applies to all charts for consistent styling
 */
export const nivoTheme: Theme = {
  background: 'transparent',

  text: {
    fontSize: 12,
    fill: 'hsl(215, 16%, 25%)',
    fontFamily: 'Open Sans, Microsoft YaHei, sans-serif',
    fontWeight: 500,
  },

  axis: {
    domain: {
      line: {
        stroke: 'hsl(215, 20%, 85%)',
        strokeWidth: 1,
      },
    },
    legend: {
      text: {
        fontSize: 13,
        fill: 'hsl(215, 16%, 35%)',
        fontWeight: 600,
      },
    },
    ticks: {
      line: {
        stroke: 'hsl(215, 20%, 85%)',
        strokeWidth: 1,
      },
      text: {
        fontSize: 11,
        fill: 'hsl(215, 16%, 45%)',
        fontWeight: 500,
      },
    },
  },

  grid: {
    line: {
      stroke: 'hsl(215, 20%, 92%)',
      strokeWidth: 1,
      strokeDasharray: '4 4',
    },
  },

  legends: {
    title: {
      text: {
        fontSize: 12,
        fill: 'hsl(215, 16%, 35%)',
        fontWeight: 600,
      },
    },
    text: {
      fontSize: 11,
      fill: 'hsl(215, 16%, 45%)',
      fontWeight: 500,
    },
    ticks: {
      line: {},
      text: {
        fontSize: 10,
        fill: 'hsl(215, 16%, 45%)',
      },
    },
  },

  annotations: {
    text: {
      fontSize: 11,
      fill: 'hsl(215, 16%, 35%)',
      outlineWidth: 2,
      outlineColor: 'hsl(0, 0%, 100%)',
      outlineOpacity: 1,
    },
    link: {
      stroke: 'hsl(215, 16%, 65%)',
      strokeWidth: 1,
      outlineWidth: 2,
      outlineColor: 'hsl(0, 0%, 100%)',
      outlineOpacity: 1,
    },
    outline: {
      stroke: 'hsl(215, 16%, 65%)',
      strokeWidth: 2,
      outlineWidth: 2,
      outlineColor: 'hsl(0, 0%, 100%)',
      outlineOpacity: 1,
    },
    symbol: {
      fill: 'hsl(215, 16%, 65%)',
      outlineWidth: 2,
      outlineColor: 'hsl(0, 0%, 100%)',
      outlineOpacity: 1,
    },
  },

  tooltip: {
    container: {
      background: 'hsl(0, 0%, 100%)',
      color: 'hsl(215, 16%, 25%)',
      fontSize: 12,
      borderRadius: '8px',
      boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
      padding: '12px 16px',
      border: '1px solid hsl(215, 20%, 90%)',
    },
    basic: {},
    chip: {},
    table: {},
    tableCell: {},
    tableCellValue: {},
  },

  labels: {
    text: {
      fontSize: 11,
      fill: 'hsl(215, 16%, 35%)',
      fontWeight: 600,
    },
  },

  dots: {
    text: {},
  },

  markers: {
    lineColor: 'hsl(215, 16%, 65%)',
    lineStrokeWidth: 1,
    textColor: 'hsl(215, 16%, 35%)',
    fontSize: 11,
  },
};

// ============================================================================
// CHART-SPECIFIC CONFIGURATIONS
// ============================================================================

/**
 * Bar chart configuration
 */
export const barChartConfig = {
  theme: nivoTheme,
  colors: chartColors,
  borderRadius: 4,
  borderWidth: 0,
  padding: 0.15,
  enableGridY: true,
  enableGridX: false,
  animate: true,
  motionConfig: 'gentle' as const,
  labelTextColor: { from: 'color', modifiers: [['darker', 1.8]] as any },
};

/**
 * Line chart configuration
 */
export const lineChartConfig = {
  theme: nivoTheme,
  colors: chartColors,
  lineWidth: 2,
  pointSize: 8,
  pointBorderWidth: 2,
  pointBorderColor: { from: 'serieColor' },
  enableGridX: false,
  enableGridY: true,
  animate: true,
  motionConfig: 'gentle' as const,
  useMesh: true,
};

/**
 * Pie/Donut chart configuration
 */
export const pieChartConfig = {
  theme: nivoTheme,
  colors: chartColors,
  borderWidth: 0,
  enableArcLabels: true,
  enableArcLinkLabels: true,
  animate: true,
  motionConfig: 'gentle' as const,
  arcLinkLabelsColor: { from: 'color' },
  arcLinkLabelsThickness: 2,
};

/**
 * Treemap configuration (for word clouds)
 */
export const treemapConfig = {
  theme: nivoTheme,
  colors: chartColors,
  borderWidth: 0,
  labelSkipSize: 12,
  animate: true,
  motionConfig: 'gentle' as const,
};

/**
 * Network graph configuration
 */
export const networkGraphConfig = {
  nodeColor: chartColors[0],
  linkColor: 'hsl(215, 20%, 85%)',
  linkWidth: 1,
  nodeSize: 8,
  activeNodeSize: 12,
  labelColor: 'hsl(215, 16%, 35%)',
  labelSize: 11,
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Get color by index with cycling
 */
export const getChartColor = (index: number): string => {
  return chartColors[index % chartColors.length];
};

/**
 * Get color array for specific count
 */
export const getChartColorArray = (count: number): string[] => {
  return Array.from({ length: count }, (_, i) => getChartColor(i));
};

/**
 * Get semantic color by type
 */
export const getSemanticColor = (
  type: keyof typeof semanticColors
): string => {
  return semanticColors[type];
};

/**
 * Generate custom color scheme from data
 */
export const generateColorScheme = (
  dataKeys: string[],
  baseColor?: string
): Record<string, string> => {
  const scheme: Record<string, string> = {};

  dataKeys.forEach((key, index) => {
    scheme[key] = baseColor
      ? adjustColor(baseColor, index * 15)
      : getChartColor(index);
  });

  return scheme;
};

/**
 * Adjust HSL color hue
 */
function adjustColor(hslColor: string, hueShift: number): string {
  const match = hslColor.match(/hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)/);
  if (!match) return hslColor;

  const [, h, s, l] = match;
  const newHue = (parseInt(h) + hueShift) % 360;

  return `hsl(${newHue}, ${s}%, ${l}%)`;
}

/**
 * Get responsive margins based on viewport
 */
export const getResponsiveMargins = (width: number) => {
  if (width < 640) {
    // Mobile
    return { top: 20, right: 20, bottom: 40, left: 40 };
  } else if (width < 1024) {
    // Tablet
    return { top: 30, right: 40, bottom: 60, left: 60 };
  } else {
    // Desktop
    return { top: 40, right: 60, bottom: 80, left: 80 };
  }
};

// ============================================================================
// CUSTOM TOOLTIP COMPONENTS
// ============================================================================

/**
 * Standardized tooltip style
 */
export const tooltipStyle = {
  container: 'bg-white p-3 shadow-lg rounded-lg border border-gray-200',
  title: 'font-semibold text-gray-900 text-sm mb-1',
  content: 'text-sm text-gray-600',
  value: 'font-medium text-gray-900',
  label: 'text-xs text-gray-500',
};

/**
 * Create standardized tooltip component
 */
export const createTooltip = (
  title: string,
  items: Array<{ label: string; value: string | number; color?: string }>
) => {
  return (
    <div className={tooltipStyle.container}>
      <div className={tooltipStyle.title}>{title}</div>
      {items.map((item, index) => (
        <div key={index} className="flex items-center justify-between gap-3 mt-1">
          {item.color && (
            <div
              className="w-3 h-3 rounded-sm flex-shrink-0"
              style={{ backgroundColor: item.color }}
            />
          )}
          <span className={tooltipStyle.label}>{item.label}:</span>
          <span className={tooltipStyle.value}>{item.value}</span>
        </div>
      ))}
    </div>
  );
};

// ============================================================================
// EXPORT DEFAULTS
// ============================================================================

export default {
  theme: nivoTheme,
  colors: chartColors,
  semanticColors,
  gradients: chartGradients,
  barChart: barChartConfig,
  lineChart: lineChartConfig,
  pieChart: pieChartConfig,
  treemap: treemapConfig,
  network: networkGraphConfig,
  utils: {
    getChartColor,
    getChartColorArray,
    getSemanticColor,
    generateColorScheme,
    getResponsiveMargins,
    createTooltip,
  },
};
