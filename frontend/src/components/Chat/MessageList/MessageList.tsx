import { useRef, useEffect } from 'react';
import { MessageBubble } from '../MessageBubble/MessageBubble';
import type { Message } from '@/types';
import './MessageList.scss';

interface MessageListProps {
  messages: Message[];
  streamingContent?: string;
  isStreaming?: boolean;
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
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      
      {isStreaming && streamingContent && (
        <MessageBubble
          message={{
            id: 'streaming',
            chat_id: '',
            parent_id: null,
            branch: 'main',
            role: 'assistant',
            message_type: 'text',
            content: streamingContent,
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
  );
}
