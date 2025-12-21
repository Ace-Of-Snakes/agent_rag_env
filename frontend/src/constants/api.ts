// API endpoint constants

export const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const API_ENDPOINTS = {
  // Health
  HEALTH: '/api/v1/health',
  HEALTH_DETAILED: '/api/v1/health/detailed',

  // Chats
  CHATS: '/api/v1/chats',
  CHAT: (id: string) => `/api/v1/chats/${id}`,
  CHAT_MESSAGES: (id: string) => `/api/v1/chats/${id}/messages`,
  CHAT_MESSAGES_STREAM: (id: string) => `/api/v1/chats/${id}/messages/stream`,
  CHAT_BRANCHES: (id: string) => `/api/v1/chats/${id}/branches`,
  CHAT_BRANCHES_SWITCH: (id: string) => `/api/v1/chats/${id}/branches/switch`,
  CHAT_HISTORY: (id: string) => `/api/v1/chats/${id}/history`,

  // Documents
  DOCUMENTS: '/api/v1/documents',
  DOCUMENT: (id: string) => `/api/v1/documents/${id}`,
  DOCUMENT_STATUS: (id: string) => `/api/v1/documents/${id}/status`,
  DOCUMENTS_SEARCH: '/api/v1/documents/search',
} as const;

// SSE event types
export const SSE_EVENTS = {
  MESSAGE: 'message',
  TOOL_START: 'tool_start',
  TOOL_END: 'tool_end',
  DONE: 'done',
  ERROR: 'error',
  THOUGHT: 'thought',
  PROGRESS: 'progress',
} as const;
