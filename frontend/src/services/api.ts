import { API_BASE_URL, API_ENDPOINTS } from '@/constants/api';
import type {
  Chat,
  ChatDetail,
  ChatListResponse,
  CreateBranchRequest,
  CreateChatRequest,
  DocumentDetail,
  DocumentListResponse,
  SearchResponse,
  SendMessageRequest,
  SwitchBranchRequest,
  UploadResponse,
} from '@/types';

// =============================================================================
// Base API Functions
// =============================================================================

interface FetchOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data?: unknown
  ) {
    super(`API Error: ${status} ${statusText}`);
    this.name = 'ApiError';
  }
}

async function apiFetch<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { params, ...fetchOptions } = options;

  // Build URL with query params
  let url = `${API_BASE_URL}${endpoint}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  // Default headers
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...fetchOptions.headers,
  };

  const response = await fetch(url, {
    ...fetchOptions,
    headers,
  });

  if (!response.ok) {
    let data: unknown;
    try {
      data = await response.json();
    } catch {
      data = null;
    }
    throw new ApiError(response.status, response.statusText, data);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// =============================================================================
// Chat API
// =============================================================================

export interface UpdateChatRequest {
  title?: string;
}

export const chatApi = {
  list: (page = 1, pageSize = 20): Promise<ChatListResponse> =>
    apiFetch(API_ENDPOINTS.CHATS, {
      params: { page, page_size: pageSize },
    }),

  get: (id: string): Promise<ChatDetail> =>
    apiFetch(API_ENDPOINTS.CHAT(id)),

  create: (data: CreateChatRequest): Promise<Chat> =>
    apiFetch(API_ENDPOINTS.CHATS, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: UpdateChatRequest): Promise<Chat> =>
    apiFetch(API_ENDPOINTS.CHAT(id), {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  updateTitle: (id: string, title: string): Promise<Chat> =>
    apiFetch(API_ENDPOINTS.CHAT(id), {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    }),

  delete: (id: string): Promise<void> =>
    apiFetch(API_ENDPOINTS.CHAT(id), {
      method: 'DELETE',
    }),

  sendMessage: (chatId: string, data: SendMessageRequest): Promise<unknown> =>
    apiFetch(API_ENDPOINTS.CHAT_MESSAGES(chatId), {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  createBranch: (chatId: string, data: CreateBranchRequest): Promise<Chat> =>
    apiFetch(API_ENDPOINTS.CHAT_BRANCHES(chatId), {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  switchBranch: (chatId: string, data: SwitchBranchRequest): Promise<Chat> =>
    apiFetch(API_ENDPOINTS.CHAT_BRANCHES_SWITCH(chatId), {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getHistory: (
    chatId: string,
    branch?: string,
    maxMessages?: number
  ): Promise<{ messages: unknown[]; count: number }> =>
    apiFetch(API_ENDPOINTS.CHAT_HISTORY(chatId), {
      params: { branch, max_messages: maxMessages },
    }),
};

// =============================================================================
// Document API
// =============================================================================

export const documentApi = {
  list: (
    page = 1,
    pageSize = 20,
    status?: string
  ): Promise<DocumentListResponse> =>
    apiFetch(API_ENDPOINTS.DOCUMENTS, {
      params: { page, page_size: pageSize, status },
    }),

  get: (id: string): Promise<DocumentDetail> =>
    apiFetch(API_ENDPOINTS.DOCUMENT(id)),

  getStatus: (id: string): Promise<{
    document_id: string;
    status: string;
    error_message: string | null;
    page_count: number | null;
    total_chunks: number;
  }> => apiFetch(API_ENDPOINTS.DOCUMENT_STATUS(id)),

  delete: (id: string): Promise<void> =>
    apiFetch(API_ENDPOINTS.DOCUMENT(id), {
      method: 'DELETE',
    }),

  upload: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.DOCUMENTS}`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let data: unknown;
      try {
        data = await response.json();
      } catch {
        data = null;
      }
      throw new ApiError(response.status, response.statusText, data);
    }

    return response.json();
  },

  search: (
    query: string,
    topK = 5,
    documentIds?: string[]
  ): Promise<SearchResponse> =>
    apiFetch(API_ENDPOINTS.DOCUMENTS_SEARCH, {
      params: {
        query,
        top_k: topK,
        document_ids: documentIds?.join(','),
      },
    }),
};

// =============================================================================
// Health API
// =============================================================================

export const healthApi = {
  check: (): Promise<{ status: string }> =>
    apiFetch(API_ENDPOINTS.HEALTH),

  detailed: (): Promise<{
    status: string;
    version: string;
    services: Record<string, { status: string; error?: string }>;
  }> => apiFetch(API_ENDPOINTS.HEALTH_DETAILED),
};

// Export error class for use in components
export { ApiError };