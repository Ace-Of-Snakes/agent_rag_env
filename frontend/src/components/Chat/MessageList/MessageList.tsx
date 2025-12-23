import { useRef, useEffect, useMemo } from 'react';
import { MessageBubble } from '../MessageBubble/MessageBubble';
import type { Message } from '@/types';
import './MessageList.scss';

interface MessageListProps {
  messages: Message[];
  streamingContent?: string;
  isStreaming?: boolean;
}

/**
 * Parse streaming content to extract response from JSON if present.
 * This helps show cleaner content during streaming.
 */
function parseStreamingContent(content: string): string {
  if (!content) return '';
  
  const trimmed = content.trim();
  
  // If we're in the middle of streaming JSON, try to extract response
  // Check if it looks like it might be JSON output
  if (trimmed.startsWith('```json') || trimmed.startsWith('{')) {
    // Try to find and extract a response field
    const responseMatch = trimmed.match(/"response"\s*:\s*"((?:[^"\\]|\\.)*)"/);
    if (responseMatch) {
      // Unescape the JSON string
      try {
        const unescaped = JSON.parse(`"${responseMatch[1]}"`);
        return unescaped;
      } catch {
        return responseMatch[1].replace(/\\n/g, '\n').replace(/\\"/g, '"');
      }
    }
    
    // If we haven't found a response yet, show a loading indicator
    // or partial content
    if (trimmed.includes('"thought"') && !trimmed.includes('"response"')) {
      return '...';
    }
  }
  
  return content;
}

export function MessageList({
  messages,
  streamingContent,
  isStreaming,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // Parse streaming content
  const displayStreamingContent = useMemo(() => {
    return parseStreamingContent(streamingContent || '');
  }, [streamingContent]);

  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="message-list message-list--empty">
        <div className="message-list__welcome">
          <h2>Welcome to RAGent</h2>
          <p>Start a conversation or upload documents to build your knowledge base.</p>
          <div className="message-list__suggestions">
            <button className="message-list__suggestion">
              What documents do I have?
            </button>
            <button className="message-list__suggestion">
              Help me understand my files
            </button>
            <button className="message-list__suggestion">
              Search for information
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="message-list">
      <div className="message-list__container">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        
        {isStreaming && displayStreamingContent && (
          <MessageBubble
            message={{
              id: 'streaming',
              chat_id: '',
              parent_id: null,
              branch: 'main',
              role: 'assistant',
              message_type: 'text',
              content: displayStreamingContent,
              token_count: null,
              tool_name: null,
              tool_params: null,
              attachments: null,
              sources: null,
              metadata: null,
              created_at: new Date().toISOString(),
            }}
            isStreaming
          />
        )}
        
        <div ref={bottomRef} />
      </div>
    </div>
  );
}