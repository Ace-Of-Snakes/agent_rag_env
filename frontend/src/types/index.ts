// =============================================================================
// Chat Types
// =============================================================================

export interface Message {
  id: string;
  chat_id: string;
  parent_id: string | null;
  branch: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  message_type: 'text' | 'file' | 'tool_call' | 'tool_result';
  content: string;
  token_count: number | null;
  tool_name: string | null;
  tool_params: Record<string, unknown> | null;
  attachments: Record<string, unknown> | null;
  sources: Source[] | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface Chat {
  id: string;
  title: string | null;
  active_branch: string;
  branches: Record<string, BranchInfo>;
  message_count: number;
  last_message_at: string | null;
  settings: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ChatDetail extends Chat {
  messages: Message[];
}

export interface BranchInfo {
  created_at: string;
  from_message_id: string | null;
}

export interface Source {
  document: string;
  page: number | null;
  content_preview: string;
}

// =============================================================================
// Document Types
// =============================================================================

export interface Document {
  id: string;
  filename: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  status: DocumentStatus;
  error_message: string | null;
  page_count: number | null;
  total_chunks: number;
  summary: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  processing_started_at: string | null;
  processing_completed_at: string | null;
}

export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface DocumentChunk {
  id: string;
  chunk_index: number;
  page_number: number | null;
  content: string;
  content_type: string;
  token_count: number | null;
  metadata: Record<string, unknown> | null;
}

export interface DocumentDetail extends Document {
  chunks: DocumentChunk[];
}

export interface SearchResult {
  chunk_id: string;
  document_id: string;
  document_filename: string;
  content: string;
  page_number: number | null;
  similarity_score: number;
  metadata: Record<string, unknown> | null;
}

// =============================================================================
// API Types
// =============================================================================

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface ChatListResponse {
  chats: Chat[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
  search_time_ms: number;
}

export interface UploadResponse {
  id: string;
  filename: string;
  original_filename: string;
  status: DocumentStatus;
  message: string;
}

// =============================================================================
// SSE Event Types
// =============================================================================

export interface SSEEvent {
  event: string;
  data: Record<string, unknown>;
}

export interface MessageTokenEvent {
  token: string;
  iteration: number;
}

export interface ToolStartEvent {
  tool: string;
  input: Record<string, unknown>;
}

export interface ToolEndEvent {
  tool: string;
  success: boolean;
  result_preview: string;
}

export interface DoneEvent {
  response: string;
  sources: Source[];
  iterations: number;
  execution_time_ms: number;
}

export interface ErrorEvent {
  error: string;
}

// =============================================================================
// Request Types
// =============================================================================

export interface CreateChatRequest {
  title?: string;
  initial_message?: string;
  settings?: Record<string, unknown>;
}

export interface SendMessageRequest {
  content: string;
  attachments?: Record<string, unknown>[];
  parent_id?: string;
  branch?: string;
}

export interface CreateBranchRequest {
  branch_name: string;
  from_message_id?: string;
}

export interface SwitchBranchRequest {
  branch_name: string;
}
