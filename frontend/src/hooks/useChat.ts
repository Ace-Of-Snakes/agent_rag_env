import { useState, useCallback, useRef, useEffect } from 'react';
import { API_BASE_URL, API_ENDPOINTS } from '@/constants/api';
import { chatApi } from '@/services/api';
import type {
  ChatDetail,
  Message,
  Source,
  SendMessageRequest,
} from '@/types';

interface UseChatOptions {
  onError?: (error: Error) => void;
}

interface StreamingState {
  isStreaming: boolean;
  currentResponse: string;
  currentTool: string | null;
  sources: Source[];
}

export function useChat(chatId: string | null, options: UseChatOptions = {}) {
  const { onError } = options;

  // State
  const [chat, setChat] = useState<ChatDetail | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [streaming, setStreaming] = useState<StreamingState>({
    isStreaming: false,
    currentResponse: '',
    currentTool: null,
    sources: [],
  });

  // Refs for SSE
  const eventSourceRef = useRef<EventSource | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Load chat data
  const loadChat = useCallback(async () => {
    if (!chatId) return;

    setIsLoading(true);
    try {
      const data = await chatApi.get(chatId);
      setChat(data);
      setMessages(data.messages || []);
    } catch (error) {
      onError?.(error as Error);
    } finally {
      setIsLoading(false);
    }
  }, [chatId, onError]);

  // Load chat on mount or chatId change
  useEffect(() => {
    loadChat();
  }, [loadChat]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
      abortControllerRef.current?.abort();
    };
  }, []);

  // Send message with streaming
  const sendMessage = useCallback(
    async (content: string, attachments?: Record<string, unknown>[]) => {
      if (!chatId || streaming.isStreaming) return;

      // Add user message optimistically
      const userMessage: Message = {
        id: `temp-${Date.now()}`,
        chat_id: chatId,
        parent_id: messages.length > 0 ? messages[messages.length - 1].id : null,
        branch: chat?.active_branch || 'main',
        role: 'user',
        message_type: 'text',
        content,
        token_count: null,
        tool_name: null,
        tool_params: null,
        attachments: attachments ? { files: attachments } : null,
        sources: null,
        metadata: null,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage]);

      // Start streaming
      setStreaming({
        isStreaming: true,
        currentResponse: '',
        currentTool: null,
        sources: [],
      });

      try {
        const url = `${API_BASE_URL}${API_ENDPOINTS.CHAT_MESSAGES_STREAM(chatId)}`;
        
        // Use fetch for POST with SSE
        abortControllerRef.current = new AbortController();
        
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            content,
            attachments,
          } as SendMessageRequest),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No response body');
        }

        const decoder = new TextDecoder();
        let buffer = '';
        let fullResponse = '';
        let sources: Source[] = [];

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          
          // Parse SSE events
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('event:')) {
              // Event type marker - data follows
              continue;
            }
            
            if (line.startsWith('data:')) {
              const dataStr = line.slice(5).trim();
              if (!dataStr) continue;

              try {
                const data = JSON.parse(dataStr);
                
                // Handle different event types based on data structure
                if ('token' in data) {
                  // Message token
                  fullResponse += data.token;
                  setStreaming((prev) => ({
                    ...prev,
                    currentResponse: fullResponse,
                  }));
                } else if ('tool' in data && 'input' in data) {
                  // Tool start
                  setStreaming((prev) => ({
                    ...prev,
                    currentTool: data.tool,
                  }));
                } else if ('tool' in data && 'success' in data) {
                  // Tool end
                  setStreaming((prev) => ({
                    ...prev,
                    currentTool: null,
                  }));
                } else if ('response' in data) {
                  // Done
                  fullResponse = data.response || fullResponse;
                  sources = data.sources || [];
                } else if ('error' in data) {
                  // Error
                  throw new Error(data.error);
                }
              } catch (e) {
                // Ignore JSON parse errors for incomplete data
                if (e instanceof SyntaxError) continue;
                throw e;
              }
            }
          }
        }

        // Add assistant message
        const assistantMessage: Message = {
          id: `temp-${Date.now()}-assistant`,
          chat_id: chatId,
          parent_id: userMessage.id,
          branch: chat?.active_branch || 'main',
          role: 'assistant',
          message_type: 'text',
          content: fullResponse,
          token_count: null,
          tool_name: null,
          tool_params: null,
          attachments: null,
          sources: sources.length > 0 ? sources : null,
          metadata: null,
          created_at: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
        setStreaming({
          isStreaming: false,
          currentResponse: '',
          currentTool: null,
          sources: [],
        });

      } catch (error) {
        if ((error as Error).name === 'AbortError') {
          // User cancelled
          return;
        }
        onError?.(error as Error);
        setStreaming({
          isStreaming: false,
          currentResponse: '',
          currentTool: null,
          sources: [],
        });
      }
    },
    [chatId, chat, messages, streaming.isStreaming, onError]
  );

  // Cancel streaming
  const cancelStreaming = useCallback(() => {
    abortControllerRef.current?.abort();
    setStreaming({
      isStreaming: false,
      currentResponse: '',
      currentTool: null,
      sources: [],
    });
  }, []);

  // Create new branch
  const createBranch = useCallback(
    async (branchName: string, fromMessageId?: string) => {
      if (!chatId) return;

      try {
        const updatedChat = await chatApi.createBranch(chatId, {
          branch_name: branchName,
          from_message_id: fromMessageId,
        });
        setChat((prev) => (prev ? { ...prev, ...updatedChat } : null));
      } catch (error) {
        onError?.(error as Error);
      }
    },
    [chatId, onError]
  );

  // Switch branch
  const switchBranch = useCallback(
    async (branchName: string) => {
      if (!chatId) return;

      try {
        const updatedChat = await chatApi.switchBranch(chatId, {
          branch_name: branchName,
        });
        setChat((prev) => (prev ? { ...prev, ...updatedChat } : null));
        // Reload messages for new branch
        await loadChat();
      } catch (error) {
        onError?.(error as Error);
      }
    },
    [chatId, loadChat, onError]
  );

  return {
    chat,
    messages,
    isLoading,
    streaming,
    sendMessage,
    cancelStreaming,
    createBranch,
    switchBranch,
    reload: loadChat,
  };
}
