/**
 * Notebook Feature Configuration - Barrel Export
 * 
 * Re-exports all configuration from their respective modules.
 */

// Environment configuration (feature flags, host/port)
export * from './env';

// File configuration (MIME types, validation, status)
export * from './file';

// UI configuration (layout, colors, animations)
// Note: We use 'export * as' to namespace the ui config and avoid conflicts
// with file config's utility functions
export {
    LAYOUT_RATIOS,
    ANIMATIONS,
    COLORS,
    SPACING,
    TYPOGRAPHY,
    PANEL_HEADERS,
    RADIUS,
    SHADOWS,
    Z_INDEX,
    BREAKPOINTS,
    RESPONSIVE_PANELS,
    SIZES,
    GRID,
    TRANSITIONS,
    STATES,
    buildGridCols,
    buildSpacing,
} from './ui';

// Re-export with aliases for backward compatibility
export { LAYOUT_RATIOS as UI_LAYOUT_RATIOS } from './ui';
