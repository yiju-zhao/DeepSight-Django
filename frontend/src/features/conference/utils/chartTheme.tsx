/**
 * Chart Theme Configuration
 *
 * Unified theme system for all Nivo charts in the conference dashboard.
 * Implements strict Huawei Design System (Black/White/Red).
 *
 * Design Philosophy:
 * - Minimalist and high contrast
 * - Primary colors: Black (#000000), White (#FFFFFF), Huawei Red (#CE0E2D)
 * - Accessibility-first (WCAG AA compliant)
 */

// ============================================================================
// COLOR PALETTE
// ============================================================================

/**
 * Primary chart colors - Monochromatic with Red Accent
 */
export const chartColors = [
  '#000000', // Black - Primary
  '#333333', // Dark Gray - Secondary
  '#666666', // Medium Gray
  '#999999', // Light Gray
  '#CE0E2D', // Huawei Red - Accent
  '#E3E3E3', // Border Gray
];

/**
 * Semantic color mapping
 */
export const semanticColors = {
  primary: '#000000',
  success: '#000000', // Use monochrome for success unless critical
  warning: '#CE0E2D', // Red for warning/attention
  error: '#CE0E2D',   // Red for error
  info: '#666666',    // Gray for info
  neutral: '#999999',
};

/**
 * Gradient definitions (Removed for Flat Minimalist Style)
 * Keeping structure for compatibility but using solid colors
 */
export const chartGradients = {
  primary: {
    from: '#000000',
    to: '#333333',
  },
  success: {
    from: '#333333',
    to: '#666666',
  },
  multi: [
    '#000000',
    '#333333',
    '#CE0E2D',
  ],
};

// ============================================================================
// NIVO THEME CONFIGURATION
// ============================================================================

export const nivoTheme = {
  background: 'transparent',

  text: {
    fontSize: 12,
    fill: '#1E1E1E',
    fontFamily: 'Open Sans, Microsoft YaHei, sans-serif',
    fontWeight: 500,
  },

  axis: {
    domain: {
      line: {
        stroke: '#E3E3E3',
        strokeWidth: 1,
      },
    },
    legend: {
      text: {
        fontSize: 12,
        fill: '#666666',
        fontWeight: 600,
      },
    },
    ticks: {
      line: {
        stroke: '#E3E3E3',
        strokeWidth: 1,
      },
      text: {
        fontSize: 11,
        fill: '#666666',
        fontWeight: 500,
      },
    },
  },

  grid: {
    line: {
      stroke: '#F5F5F5',
      strokeWidth: 1,
      strokeDasharray: '4 4',
    },
  },

  legends: {
    title: {
      text: {
        fontSize: 12,
        fill: '#666666',
        fontWeight: 600,
      },
    },
    text: {
      fontSize: 11,
      fill: '#666666',
      fontWeight: 500,
    },
    ticks: {
      line: {},
      text: {
        fontSize: 10,
        fill: '#666666',
      },
    },
  },

  annotations: {
    text: {
      fontSize: 11,
      fill: '#1E1E1E',
      outlineWidth: 2,
      outlineColor: '#FFFFFF',
      outlineOpacity: 1,
    },
    link: {
      stroke: '#666666',
      strokeWidth: 1,
      outlineWidth: 2,
      outlineColor: '#FFFFFF',
      outlineOpacity: 1,
    },
    outline: {
      stroke: '#666666',
      strokeWidth: 2,
      outlineWidth: 2,
      outlineColor: '#FFFFFF',
      outlineOpacity: 1,
    },
    symbol: {
      fill: '#666666',
      outlineWidth: 2,
      outlineColor: '#FFFFFF',
      outlineOpacity: 1,
    },
  },

  tooltip: {
    container: {
      background: '#FFFFFF',
      color: '#1E1E1E',
      fontSize: 12,
      borderRadius: '8px',
      boxShadow: '0 8px 12px rgba(0, 0, 0, 0.08)',
      padding: '12px 16px',
      border: '1px solid #E3E3E3',
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
      fill: '#1E1E1E',
      fontWeight: 600,
    },
  },

  dots: {
    text: {},
  },

  markers: {
    lineColor: '#666666',
    lineStrokeWidth: 1,
    textColor: '#1E1E1E',
    fontSize: 11,
  },
};

// ============================================================================
// CHART-SPECIFIC CONFIGURATIONS
// ============================================================================

export const barChartConfig = {
  theme: nivoTheme,
  colors: chartColors,
  borderRadius: 0, // Zero radius for sharper, more professional look
  borderWidth: 0,
  padding: 0.15,
  enableGridY: true,
  enableGridX: false,
  animate: true,
  motionConfig: 'gentle' as const,
  labelTextColor: { from: 'color', modifiers: [['darker', 1.8]] as any },
};

export const lineChartConfig = {
  theme: nivoTheme,
  colors: chartColors,
  lineWidth: 2,
  pointSize: 6,
  pointBorderWidth: 2,
  pointBorderColor: { from: 'serieColor' },
  enableGridX: false,
  enableGridY: true,
  animate: true,
  motionConfig: 'gentle' as const,
  useMesh: true,
};

export const pieChartConfig = {
  theme: nivoTheme,
  colors: chartColors,
  borderWidth: 1,
  borderColor: '#FFFFFF',
  enableArcLabels: true,
  enableArcLinkLabels: true,
  animate: true,
  motionConfig: 'gentle' as const,
  arcLinkLabelsColor: { from: 'color' },
  arcLinkLabelsThickness: 1,
};

export const treemapConfig = {
  theme: nivoTheme,
  colors: chartColors,
  borderWidth: 1,
  borderColor: '#FFFFFF',
  labelSkipSize: 12,
  animate: true,
  motionConfig: 'gentle' as const,
};

export const networkGraphConfig = {
  nodeColor: '#000000',
  linkColor: '#E3E3E3',
  linkWidth: 1,
  nodeSize: 8,
  activeNodeSize: 12,
  labelColor: '#1E1E1E',
  labelSize: 11,
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

export const getChartColor = (index: number): string => {
  return chartColors[index % chartColors.length]!;
};

export const getChartColorArray = (count: number): string[] => {
  return Array.from({ length: count }, (_, i) => getChartColor(i));
};

export const getSemanticColor = (
  type: keyof typeof semanticColors
): string => {
  return semanticColors[type];
};

export const generateColorScheme = (
  dataKeys: string[],
  baseColor?: string
): Record<string, string> => {
  const scheme: Record<string, string> = {};
  dataKeys.forEach((key, index) => {
    scheme[key] = getChartColor(index);
  });
  return scheme;
};

export const getResponsiveMargins = (width: number) => {
  if (width < 640) {
    return { top: 20, right: 20, bottom: 40, left: 40 };
  } else if (width < 1024) {
    return { top: 30, right: 40, bottom: 60, left: 60 };
  } else {
    return { top: 40, right: 60, bottom: 80, left: 80 };
  }
};

// ============================================================================
// CUSTOM TOOLTIP COMPONENTS
// ============================================================================

export const tooltipStyle = {
  container: 'bg-white p-3 shadow-lg rounded-lg border border-gray-200',
  title: 'font-semibold text-gray-900 text-sm mb-1',
  content: 'text-sm text-gray-600',
  value: 'font-medium text-gray-900',
  label: 'text-xs text-gray-500',
};

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
              className="w-2 h-2 rounded-full flex-shrink-0"
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
