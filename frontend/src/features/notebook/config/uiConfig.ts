/**
 * UI Configuration constants for the notebook feature
 * Centralizes styling, animations, and UI behavior settings
 */

// Layout configurations
export const LAYOUT_RATIOS = {
  sources: 3,    // 3fr for sources panel
  chat: 6.5,     // 6.5fr for chat panel  
  studio: 4.5    // 4.5fr for studio panel
};

// Animation configurations
export const ANIMATIONS = {
  duration: {
    fast: 0.2,
    normal: 0.3,
    slow: 0.5
  },
  easing: {
    easeOut: "easeOut",
    easeIn: "easeIn",
    spring: "spring"
  },
  delays: {
    suggestion: 0.4,
    suggestionItem: 0.08,
    stagger: 0.05
  }
};

// Color themes - Unified color system for deepdive pages
export const COLORS = {
  // Main theme colors (Huawei Red based)
  theme: {
    primary: {
      50: '#fef2f2',   // bg-red-50
      100: '#fee2e2',  // bg-red-100
      200: '#fecaca',  // bg-red-200
      300: '#fca5a5',  // bg-red-300
      400: '#f87171',  // bg-red-400
      500: '#CE0E2D',  // Huawei Red
      600: '#A20A22',  // Huawei Red Hover
      700: '#b91c1c',  // bg-red-700
      800: '#991b1b',  // bg-red-800
      900: '#7f1d1d'   // bg-red-900
    },
    secondary: {
      50: '#f9fafb',   // bg-gray-50
      100: '#f3f4f6',  // bg-gray-100
      200: '#e5e7eb',  // bg-gray-200
      300: '#d1d5db',  // bg-gray-300
      400: '#9ca3af',  // bg-gray-400
      500: '#6b7280',  // bg-gray-500
      600: '#4b5563',  // bg-gray-600
      700: '#374151',  // bg-gray-700
      800: '#1f2937',  // bg-gray-800
      900: '#111827'   // bg-gray-900
    },
    success: {
      400: '#4ade80',  // bg-green-400
      500: '#22c55e',  // bg-green-500
      600: '#16a34a'   // bg-green-600
    },
    warning: {
      400: '#facc15',  // bg-yellow-400
      500: '#eab308',  // bg-yellow-500
      600: '#ca8a04'   // bg-yellow-600
    },
    error: {
      400: '#f87171',  // bg-red-400
      500: '#ef4444',  // bg-red-500
      600: '#dc2626'   // bg-red-600
    }
  },

  // Tailwind class shortcuts for convenience
  tw: {
    primary: {
      bg: {
        50: 'bg-red-50',
        100: 'bg-red-100',
        200: 'bg-red-200',
        300: 'bg-red-300',
        400: 'bg-red-400',
        500: 'bg-[#CE0E2D]',
        600: 'bg-[#A20A22]',
        700: 'bg-red-700',
        800: 'bg-red-800',
        900: 'bg-red-900'
      },
      text: {
        50: 'text-red-50',
        100: 'text-red-100',
        200: 'text-red-200',
        300: 'text-red-300',
        400: 'text-red-400',
        500: 'text-[#CE0E2D]',
        600: 'text-[#A20A22]',
        700: 'text-red-700',
        800: 'text-red-800',
        900: 'text-red-900'
      },
      border: {
        200: 'border-red-200',
        300: 'border-red-300',
        400: 'border-red-400',
        500: 'border-[#CE0E2D]',
        600: 'border-[#A20A22]'
      },
      hover: {
        bg: {
          600: 'hover:bg-[#A20A22]',
          700: 'hover:bg-red-700'
        },
        text: {
          600: 'hover:text-[#A20A22]',
          700: 'hover:text-red-700'
        },
        border: {
          300: 'hover:border-red-300',
          400: 'hover:border-red-400'
        }
      }
    },
    secondary: {
      bg: {
        50: 'bg-gray-50',
        100: 'bg-gray-100',
        200: 'bg-gray-200',
        700: 'bg-gray-700',
        800: 'bg-gray-800',
        900: 'bg-gray-900'
      },
      text: {
        400: 'text-gray-400',
        500: 'text-gray-500',
        600: 'text-gray-600',
        700: 'text-gray-700',
        800: 'text-gray-800',
        900: 'text-gray-900'
      },
      border: {
        200: 'border-gray-200',
        300: 'border-gray-300',
        400: 'border-gray-400'
      }
    }
  },

  // Component-specific color schemes
  components: {
    button: {
      primary: 'bg-[#000000] hover:opacity-80 text-white rounded-md transition-opacity duration-300', // Huawei Black Button
      secondary: 'bg-white text-[#000000] hover:opacity-80 rounded-md transition-opacity duration-300', // Huawei White Button
      outline: 'bg-transparent border border-black/30 text-black hover:border-black rounded-md transition-colors duration-300', // Huawei Outline
      accent: 'bg-[#CE0E2D] hover:bg-[#A20A22] text-white rounded-md transition-colors duration-300' // Huawei Red Button
    },
    modal: {
      background: 'bg-white',
      overlay: 'bg-black/60',
      header: 'bg-white border-b border-gray-100',
      border: 'border-gray-200'
    },
    form: {
      input: 'bg-transparent border-b border-black/10 focus:border-black text-[24px] placeholder:text-[#B2B2B2] p-4', // Huawei Search Input style
      label: 'text-[#1E1E1E] font-medium',
      error: 'text-[#CE0E2D]'
    },
    notification: {
      success: 'bg-gray-50 border-green-200 text-green-800',
      error: 'bg-red-50 border-red-200 text-red-800',
      warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
      info: 'bg-gray-50 border-gray-200 text-gray-800'
    }
  },

  // Panel-specific color schemes
  panels: {
    // Common background for all panels
    commonBackground: 'bg-white',
    sources: {
      background: 'bg-white',
      ring: '',
      text: 'text-[#1E1E1E]',
      textHover: 'text-black'
    },
    chat: {
      background: 'bg-white',
      ring: '',
      text: 'text-[#1E1E1E]',
      textHover: 'text-black'
    },
    studio: {
      background: 'bg-white',
      ring: '',
      text: 'text-[#1E1E1E]',
      textHover: 'text-black'
    }
  },

  // Legacy support (for backward compatibility)
  primary: {
    50: 'from-red-50',
    100: 'bg-red-100',
    500: 'bg-[#CE0E2D]',
    600: 'bg-[#A20A22]',
    700: 'bg-red-700'
  },
  secondary: {
    50: 'from-gray-50',
    100: 'bg-gray-100',
    500: 'bg-gray-500',
    600: 'bg-gray-600',
    700: 'bg-gray-700'
  },
  accent: {
    purple: {
      500: 'bg-purple-500',
      600: 'bg-purple-600'
    },
    red: {
      500: 'bg-[#CE0E2D]',
      600: 'bg-[#A20A22]'
    },
    green: {
      500: 'bg-green-500',
      600: 'bg-green-600'
    }
  }
};

// Spacing configurations
export const SPACING = {
  panel: {
    padding: 'p-6',
    margin: 'm-0',
    gap: 'gap-6'
  },
  component: {
    padding: 'p-6',
    margin: 'm-6',
    gap: 'gap-6'
  },
  item: {
    padding: 'p-3',
    margin: 'm-3',
    gap: 'gap-3'
  }
};

// Typography configurations
export const TYPOGRAPHY = {
  heading: {
    h1: 'text-[28px] leading-[1.321] font-bold text-[#1E1E1E]',
    h2: 'text-[24px] leading-[1.25] font-bold text-[#1E1E1E]',
    h3: 'text-[20px] leading-[1.5] font-bold text-[#1E1E1E]',
    h4: 'text-[16px] leading-[1.6] font-bold text-[#1E1E1E]'
  },
  body: {
    large: 'text-[16px] leading-[1.6] text-[#1E1E1E]',
    normal: 'text-[14px] leading-[1.6] text-[#666666]',
    small: 'text-[12px] leading-[1.5] text-[#666666]'
  },
  weight: {
    light: 'font-light',
    normal: 'font-normal',
    medium: 'font-medium',
    semibold: 'font-semibold',
    bold: 'font-bold',
    extrabold: 'font-extrabold'
  }
};

// Panel header configurations for consistency (DeepDive panels)
export const PANEL_HEADERS = {
  container: 'flex-shrink-0 px-6 py-5 bg-white border-b border-[#F7F7F7]',
  separator: '',
  layout: 'flex items-center justify-between',
  iconContainer: 'hidden', // Icons removed for cleaner look per Huawei style
  icon: 'h-5 w-5 text-[#1E1E1E]',
  title: 'text-[20px] font-bold text-[#1E1E1E] leading-[1.5]',
  titleContainer: 'flex items-center gap-3',
  actionsContainer: 'flex items-center gap-3'
};

// Border radius configurations
export const RADIUS = {
  small: 'rounded-sm', // 4px
  normal: 'rounded-md', // 6px
  large: 'rounded-lg', // 8px
  xl: 'rounded-2xl', // 16px
  full: 'rounded-full'
};

// Shadow configurations
export const SHADOWS = {
  small: 'shadow-[0_2px_4px_rgba(0,0,0,0.05)]',
  normal: 'shadow-[0_8px_12px_rgba(0,0,0,0.08)]', // Huawei Card Shadow
  large: 'shadow-[0_12px_20px_rgba(0,0,0,0.12)]', // Huawei Hover Shadow
  xl: 'shadow-xl',
  // Minimal panel shadows - no borders for cleaner look
  panel: {
    base: 'shadow-[0_8px_12px_rgba(0,0,0,0.08)]',
    hover: 'shadow-[0_12px_20px_rgba(0,0,0,0.12)]',
    elevated: 'shadow-[0_8px_12px_rgba(0,0,0,0.08)]'
  }
};

// Z-index configurations
export const Z_INDEX = {
  modal: 'z-[100]',
  overlay: 'z-[90]',
  dropdown: 'z-[80]',
  header: 'z-10'
};

// Responsive breakpoints
export const BREAKPOINTS = {
  sm: 'sm:',
  md: 'md:',
  lg: 'lg:',
  xl: 'xl:',
  '2xl': '2xl:'
};

// Responsive panel configurations
export const RESPONSIVE_PANELS = {
  mobile: {
    gap: 'gap-4',
    padding: 'p-4',
    radius: 'rounded-lg'
  },
  tablet: {
    gap: 'gap-6',
    padding: 'p-6',
    radius: 'rounded-lg'
  },
  desktop: {
    gap: 'gap-6',
    padding: 'p-6',
    radius: 'rounded-lg'
  }
};

// Component size configurations
export const SIZES = {
  icon: {
    small: 'h-3 w-3',
    normal: 'h-4 w-4',
    large: 'h-5 w-5',
    xl: 'h-6 w-6'
  },
  button: {
    small: 'h-[32px] px-[17px] text-[12px]',
    normal: 'h-[36px] px-[16px] text-[13px]',
    large: 'h-[48px] px-[31px] text-[13px]'
  },
  input: {
    small: 'h-8 px-3 text-xs',
    normal: 'h-10 px-3 text-sm',
    large: 'h-12 px-4 text-base'
  }
};

// Grid configurations
export const GRID = {
  cols: {
    1: 'grid-cols-1',
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-4',
    responsive: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'
  },
  gap: {
    small: 'gap-3',
    normal: 'gap-4',
    large: 'gap-6'
  }
};

// Transition configurations
export const TRANSITIONS = {
  all: 'transition-all',
  colors: 'transition-colors',
  transform: 'transition-transform',
  opacity: 'transition-opacity',
  duration: {
    fast: 'duration-200',
    normal: 'duration-300',
    slow: 'duration-500'
  }
};

// State configurations
export const STATES = {
  hover: {
    scale: 'hover:scale-[1.02]',
    bg: 'hover:bg-gray-50',
    text: 'hover:text-[#CE0E2D]'
  },
  focus: {
    ring: 'focus:ring-1 focus:ring-black',
    outline: 'focus:outline-none'
  },
  active: {
    scale: 'active:scale-[0.98]',
    bg: 'active:bg-gray-100'
  },
  disabled: {
    opacity: 'disabled:opacity-40',
    cursor: 'disabled:cursor-not-allowed'
  }
};

// Layout utility functions
export const buildGridCols = (count: number): string => {
  const colMap: Record<number, string> = {
    1: 'grid-cols-1',
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-4',
    5: 'grid-cols-5',
    6: 'grid-cols-6'
  };
  return colMap[count] || 'grid-cols-1';
};

export const buildSpacing = (size: 'xs' | 'sm' | 'md' | 'lg' | 'xl'): string => {
  const sizeMap: Record<string, string> = {
    xs: 'gap-1 p-1',
    sm: 'gap-2 p-2',
    md: 'gap-4 p-4',
    lg: 'gap-6 p-6',
    xl: 'gap-8 p-8'
  };
  return sizeMap[size] || sizeMap.md || 'gap-4 p-4';
};
