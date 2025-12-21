import ReactMarkdown from 'react-markdown';
import type { Message } from '@/types';
import './MessageBubble.scss';

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
}

export function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';

  return (
    <div className={`message ${isUser ? 'message--user' : 'message--assistant'}`}>
      <div className="message__avatar">
        {isUser ? (
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
          </svg>
        )}
      </div>
      
      <div className="message__content">
        <div className="message__bubble">
          {isAssistant ? (
            <ReactMarkdown
              components={{
                pre: ({ children }) => (
                  <pre className="message__code-block">{children}</pre>
                ),
                code: ({ children }) => (
                  <code className="message__code">{children}</code>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          ) : (
            <p>{message.content}</p>
          )}
          
          {isStreaming && (
            <span className="message__cursor" />
          )}
        </div>
        
        {message.sources && message.sources.length > 0 && (
          <div className="message__sources">
            <span className="message__sources-label">Sources:</span>
            {message.sources.map((source, index) => (
              <span key={index} className="message__source">
                {source.document}
                {source.page && ` (p. ${source.page})`}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
