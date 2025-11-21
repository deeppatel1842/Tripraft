/**
 * Design System - Theme Configuration
 * Centralized design tokens following industry standards (Material Design, Ant Design, Chakra UI)
 * All colors, spacing, typography, and other design values in one place
 */

export const theme = {
  // ============================================================================
  // COLOR PALETTE
  // ============================================================================
  colors: {
    // Primary brand colors
    primary: {
      50: '#f5f3ff',
      100: '#ede9fe',
      200: '#ddd6fe',
      300: '#c4b5fd',
      400: '#a78bfa',
      500: '#8b5cf6',  // Main primary
      600: '#7c3aed',
      700: '#6d28d9',
      800: '#5b21b6',
      900: '#4c1d95',
    },

    // Secondary colors
    secondary: {
      50: '#eff6ff',
      100: '#dbeafe',
      200: '#bfdbfe',
      300: '#93c5fd',
      400: '#60a5fa',
      500: '#3b82f6',  // Main secondary
      600: '#2563eb',
      700: '#1d4ed8',
      800: '#1e40af',
      900: '#1e3a8a',
    },

    // Neutral/Gray scale
    gray: {
      50: '#f9fafb',
      100: '#f3f4f6',
      200: '#e5e7eb',
      300: '#d1d5db',
      400: '#9ca3af',
      500: '#6b7280',
      600: '#4b5563',
      700: '#374151',
      800: '#1f2937',
      900: '#111827',
    },

    // Semantic colors
    success: {
      50: '#f0fdf4',
      100: '#dcfce7',
      500: '#22c55e',  // Main success
      600: '#16a34a',
      700: '#15803d',
    },

    error: {
      50: '#fef2f2',
      100: '#fee2e2',
      500: '#ef4444',  // Main error
      600: '#dc2626',
      700: '#b91c1c',
    },

    warning: {
      50: '#fffbeb',
      100: '#fef3c7',
      500: '#f59e0b',  // Main warning
      600: '#d97706',
      700: '#b45309',
    },

    info: {
      50: '#eff6ff',
      100: '#dbeafe',
      500: '#3b82f6',  // Main info
      600: '#2563eb',
      700: '#1d4ed8',
    },

    // Background colors
    background: {
      primary: '#ffffff',
      secondary: '#f9fafb',
      tertiary: '#f3f4f6',
      dark: '#1f2937',
    },

    // Text colors
    text: {
      primary: '#111827',
      secondary: '#4b5563',
      tertiary: '#6b7280',
      disabled: '#9ca3af',
      inverse: '#ffffff',
    },

    // Border colors
    border: {
      light: '#e5e7eb',
      default: '#d1d5db',
      dark: '#9ca3af',
    },
  },

  // ============================================================================
  // SPACING SCALE
  // ============================================================================
  spacing: {
    0: '0',
    1: '0.25rem',    // 4px
    2: '0.5rem',     // 8px
    3: '0.75rem',    // 12px
    4: '1rem',       // 16px
    5: '1.25rem',    // 20px
    6: '1.5rem',     // 24px
    8: '2rem',       // 32px
    10: '2.5rem',    // 40px
    12: '3rem',      // 48px
    16: '4rem',      // 64px
    20: '5rem',      // 80px
    24: '6rem',      // 96px
  },

  // ============================================================================
  // TYPOGRAPHY
  // ============================================================================
  typography: {
    fontFamily: {
      sans: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif",
      mono: "'Fira Code', 'Courier New', monospace",
    },

    fontSize: {
      xs: '0.75rem',      // 12px
      sm: '0.875rem',     // 14px
      base: '1rem',       // 16px
      lg: '1.125rem',     // 18px
      xl: '1.25rem',      // 20px
      '2xl': '1.5rem',    // 24px
      '3xl': '1.875rem',  // 30px
      '4xl': '2.25rem',   // 36px
      '5xl': '3rem',      // 48px
    },

    fontWeight: {
      light: 300,
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
      extrabold: 800,
    },

    lineHeight: {
      tight: 1.25,
      normal: 1.5,
      relaxed: 1.75,
    },
  },

  // ============================================================================
  // BORDER RADIUS
  // ============================================================================
  borderRadius: {
    none: '0',
    sm: '0.125rem',   // 2px
    default: '0.25rem', // 4px
    md: '0.375rem',   // 6px
    lg: '0.5rem',     // 8px
    xl: '0.75rem',    // 12px
    '2xl': '1rem',    // 16px
    full: '9999px',
  },

  // ============================================================================
  // SHADOWS
  // ============================================================================
  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    default: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
    xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
    '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
    inner: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)',
  },

  // ============================================================================
  // TRANSITIONS
  // ============================================================================
  transitions: {
    fast: '150ms ease-in-out',
    default: '200ms ease-in-out',
    slow: '300ms ease-in-out',
  },

  // ============================================================================
  // Z-INDEX SCALE
  // ============================================================================
  zIndex: {
    dropdown: 1000,
    sticky: 1020,
    fixed: 1030,
    modalBackdrop: 1040,
    modal: 1050,
    popover: 1060,
    tooltip: 1070,
  },

  // ============================================================================
  // BREAKPOINTS
  // ============================================================================
  breakpoints: {
    xs: '0px',
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px',
    '2xl': '1536px',
  },
};

// ============================================================================
// COMPONENT-SPECIFIC CONSTANTS
// ============================================================================

export const componentStyles = {
  // Button variants
  button: {
    primary: {
      background: theme.colors.primary[600],
      hoverBackground: theme.colors.primary[700],
      activeBackground: theme.colors.primary[800],
      color: theme.colors.text.inverse,
    },
    secondary: {
      background: theme.colors.secondary[600],
      hoverBackground: theme.colors.secondary[700],
      activeBackground: theme.colors.secondary[800],
      color: theme.colors.text.inverse,
    },
    success: {
      background: theme.colors.success[500],
      hoverBackground: theme.colors.success[600],
      activeBackground: theme.colors.success[700],
      color: theme.colors.text.inverse,
    },
    danger: {
      background: theme.colors.error[500],
      hoverBackground: theme.colors.error[600],
      activeBackground: theme.colors.error[700],
      color: theme.colors.text.inverse,
    },
    ghost: {
      background: 'transparent',
      hoverBackground: theme.colors.gray[100],
      activeBackground: theme.colors.gray[200],
      color: theme.colors.text.primary,
    },
  },

  // Input styles
  input: {
    borderColor: theme.colors.border.default,
    focusBorderColor: theme.colors.primary[500],
    errorBorderColor: theme.colors.error[500],
    backgroundColor: theme.colors.background.primary,
    placeholderColor: theme.colors.text.tertiary,
  },

  // Card styles
  card: {
    background: theme.colors.background.primary,
    borderColor: theme.colors.border.light,
    shadow: theme.shadows.md,
    hoverShadow: theme.shadows.lg,
  },
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Get color from theme
 * @param {string} path - Color path (e.g., 'primary.500', 'gray.100')
 * @returns {string} Color value
 */
export const getColor = (path) => {
  const keys = path.split('.');
  let value = theme.colors;
  for (const key of keys) {
    value = value[key];
    if (!value) return theme.colors.gray[500]; // Fallback
  }
  return value;
};

/**
 * Get spacing value
 * @param {number|string} size - Spacing size
 * @returns {string} Spacing value
 */
export const getSpacing = (size) => {
  return theme.spacing[size] || theme.spacing[4]; // Fallback to 1rem
};

/**
 * Generate CSS variables for theming
 * @returns {object} CSS variables object
 */
export const generateCSSVariables = () => {
  return {
    '--color-primary': theme.colors.primary[500],
    '--color-secondary': theme.colors.secondary[500],
    '--color-success': theme.colors.success[500],
    '--color-error': theme.colors.error[500],
    '--color-warning': theme.colors.warning[500],
    '--color-info': theme.colors.info[500],
    
    '--color-text-primary': theme.colors.text.primary,
    '--color-text-secondary': theme.colors.text.secondary,
    '--color-text-tertiary': theme.colors.text.tertiary,
    
    '--color-bg-primary': theme.colors.background.primary,
    '--color-bg-secondary': theme.colors.background.secondary,
    
    '--color-border': theme.colors.border.default,
    
    '--spacing-base': theme.spacing[4],
    '--radius-default': theme.borderRadius.default,
    '--shadow-default': theme.shadows.default,
    '--transition-default': theme.transitions.default,
  };
};

export default theme;
