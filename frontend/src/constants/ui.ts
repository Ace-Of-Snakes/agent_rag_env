// UI constants

export const UI = {
  // Sidebar
  SIDEBAR_WIDTH: 280,
  SIDEBAR_COLLAPSED_WIDTH: 60,

  // Chat
  MAX_MESSAGE_LENGTH: 10000,
  MESSAGE_HISTORY_LIMIT: 100,

  // Documents
  MAX_FILE_SIZE_MB: 50,
  SUPPORTED_FILE_TYPES: ['.pdf'],

  // Animation durations (ms)
  ANIMATION_FAST: 150,
  ANIMATION_NORMAL: 300,
  ANIMATION_SLOW: 500,

  // Debounce delays (ms)
  DEBOUNCE_SEARCH: 300,
  DEBOUNCE_RESIZE: 100,

  // Breakpoints
  BREAKPOINT_SM: 640,
  BREAKPOINT_MD: 768,
  BREAKPOINT_LG: 1024,
  BREAKPOINT_XL: 1280,
} as const;

// Document status labels
export const DOCUMENT_STATUS_LABELS: Record<string, string> = {
  pending: 'Pending',
  processing: 'Processing',
  completed: 'Completed',
  failed: 'Failed',
};

// Document status colors
export const DOCUMENT_STATUS_COLORS: Record<string, string> = {
  pending: '#f59e0b',
  processing: '#3b82f6',
  completed: '#10b981',
  failed: '#ef4444',
};
