import { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import { CodeBlock } from '../CodeBlock/CodeBlock';
import type { Message } from '@/types';
import './MessageBubble.scss';

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
}

/**
 * Attempts to parse the content if it's a JSON agent response
 * and extract the actual response text.
 */
function parseContent(content: string): string {
  if (!content) return '';
  
  const trimmed = content.trim();
  
  // Check if the entire content is wrapped in a JSON code block
  // Pattern: ```json\n{...}\n``` or ```\n{...}\n```
  const jsonCodeBlockRegex = /^```(?:json)?\s*\n([\s\S]+)\n```\s*$/;
  const jsonCodeBlockMatch = trimmed.match(jsonCodeBlockRegex);
  
  if (jsonCodeBlockMatch) {
    const jsonContent = jsonCodeBlockMatch[1].trim();
    try {
      const parsed = JSON.parse(jsonContent);
      if (typeof parsed === 'object' && parsed !== null && 'response' in parsed) {
        return parsed.response;
      }
    } catch {
      // Not valid JSON, continue
    }
  }
  
  // Check if it's raw JSON (starts with { and ends with })
  if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
    try {
      const parsed = JSON.parse(trimmed);
      // Check if it's an agent response with thought/action/response structure
      if (typeof parsed === 'object' && parsed !== null) {
        // Return the response field if it exists
        if ('response' in parsed && typeof parsed.response === 'string') {
          return parsed.response;
        }
        // Sometimes the actual content might be in a message field
        if ('message' in parsed && typeof parsed.message === 'string') {
          return parsed.message;
        }
      }
    } catch {
      // Not valid JSON, return as-is
    }
  }
  
  // Check for JSON at the start followed by other content
  // This handles cases where the LLM outputs JSON and then continues
  const jsonStartMatch = trimmed.match(/^```(?:json)?\s*\n(\{[\s\S]*?\})\n```/);
  if (jsonStartMatch) {
    try {
      const parsed = JSON.parse(jsonStartMatch[1]);
      if (parsed.response) {
        return parsed.response;
      }
    } catch {
      // Continue
    }
  }
  
  return content;
}

export function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';

  // Parse and clean the content
  const displayContent = useMemo(() => {
    if (isAssistant) {
      return parseContent(message.content);
    }
    return message.content;
  }, [message.content, isAssistant]);

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
                // Handle code blocks
                pre: ({ children }) => {
                  return <>{children}</>;
                },
                code: ({ className, children }) => {
                  // Check if it's a code block (has language class) or inline code
                  const match = /language-(\w+)/.exec(className || '');
                  const codeContent = String(children).replace(/\n$/, '');
                  
                  // If it has a language class or is multiline, treat as code block
                  const isCodeBlock = match || codeContent.includes('\n');
                  
                  if (isCodeBlock) {
                    return (
                      <CodeBlock 
                        code={codeContent}
                        language={match ? match[1] : undefined}
                      />
                    );
                  }
                  
                  // Inline code
                  return (
                    <CodeBlock 
                      code={codeContent}
                      inline
                    />
                  );
                },
                // Style paragraphs
                p: ({ children }) => (
                  <p className="message__paragraph">{children}</p>
                ),
                // Style lists
                ul: ({ children }) => (
                  <ul className="message__list message__list--unordered">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="message__list message__list--ordered">{children}</ol>
                ),
                li: ({ children }) => (
                  <li className="message__list-item">{children}</li>
                ),
                // Style headings
                h1: ({ children }) => (
                  <h1 className="message__heading message__heading--1">{children}</h1>
                ),
                h2: ({ children }) => (
                  <h2 className="message__heading message__heading--2">{children}</h2>
                ),
                h3: ({ children }) => (
                  <h3 className="message__heading message__heading--3">{children}</h3>
                ),
                // Style links
                a: ({ href, children }) => (
                  <a href={href} className="message__link" target="_blank" rel="noopener noreferrer">
                    {children}
                  </a>
                ),
                // Style blockquotes
                blockquote: ({ children }) => (
                  <blockquote className="message__blockquote">{children}</blockquote>
                ),
                // Style horizontal rules
                hr: () => <hr className="message__hr" />,
                // Style strong/bold
                strong: ({ children }) => (
                  <strong className="message__strong">{children}</strong>
                ),
                // Style emphasis/italic
                em: ({ children }) => (
                  <em className="message__em">{children}</em>
                ),
              }}
            >
              {displayContent}
            </ReactMarkdown>
          ) : (
            <p>{displayContent}</p>
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