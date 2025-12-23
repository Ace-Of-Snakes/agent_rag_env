import { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import { CodeBlock } from '../CodeBlock/CodeBlock';
import type { Message, Source } from '@/types';
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
  
  // Check if it's raw JSON
  if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
    try {
      const parsed = JSON.parse(trimmed);
      if (typeof parsed === 'object' && parsed !== null) {
        if ('response' in parsed && typeof parsed.response === 'string') {
          return parsed.response;
        }
        if ('message' in parsed && typeof parsed.message === 'string') {
          return parsed.message;
        }
      }
    } catch {
      // Not valid JSON, return as-is
    }
  }
  
  // Check for JSON at the start followed by other content
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

/**
 * Normalize sources from various formats the backend might send.
 */
function normalizeSources(sources: unknown): Source[] {
  if (!sources) return [];
  
  // Handle {sources: [...]} wrapper from backend
  if (typeof sources === 'object' && sources !== null && 'sources' in sources) {
    const wrapper = sources as { sources: unknown };
    return normalizeSources(wrapper.sources);
  }
  
  // Handle direct array
  if (Array.isArray(sources)) {
    return sources
      .filter((s) => s && typeof s === 'object')
      .map((s, idx) => ({
        document: s.document || s.document_filename || s.title || 'Unknown',
        page: s.page ?? s.page_number ?? null,
        content_preview: s.content_preview || (s.content ? s.content.slice(0, 150) : ''),
        chunk_id: s.chunk_id,
        similarity: s.similarity ?? s.similarity_score,
        url: s.url,
        index: s.index ?? idx + 1,
      }));
  }
  
  return [];
}

/**
 * Source citation component
 */
function SourceCitation({ source }: { source: Source }) {
  const isWebSource = !!source.url;
  
  return (
    <div className="source-citation">
      <span className="source-citation__index">[{source.index}]</span>
      {isWebSource ? (
        <a 
          href={source.url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="source-citation__link"
        >
          {source.document}
        </a>
      ) : (
        <span className="source-citation__document">{source.document}</span>
      )}
      {source.page && (
        <span className="source-citation__page">p. {source.page}</span>
      )}
      {source.similarity && (
        <span className="source-citation__similarity">
          {Math.round(source.similarity * 100)}%
        </span>
      )}
    </div>
  );
}

/**
 * Sources panel component
 */
function SourcesPanel({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return null;
  
  return (
    <div className="sources-panel">
      <div className="sources-panel__header">
        <svg 
          className="sources-panel__icon" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          strokeWidth="2"
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14,2 14,8 20,8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
        </svg>
        <span>Sources ({sources.length})</span>
      </div>
      <div className="sources-panel__list">
        {sources.map((source, idx) => (
          <SourceCitation key={source.chunk_id || `source-${idx}`} source={source} />
        ))}
      </div>
    </div>
  );
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

  // Normalize sources
  const sources = useMemo(() => {
    return normalizeSources(message.sources);
  }, [message.sources]);

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
          <ReactMarkdown
            components={{
              code({ node, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                const isInline = !match && !String(children).includes('\n');
                
                if (isInline) {
                  return (
                    <code className="inline-code" {...props}>
                      {children}
                    </code>
                  );
                }
                
                return (
                  <CodeBlock
                    language={match ? match[1] : 'text'}
                    code={String(children).replace(/\n$/, '')}
                  />
                );
              },
            }}
          >
            {displayContent}
          </ReactMarkdown>
          
          {isStreaming && (
            <span className="message__cursor" />
          )}
        </div>
        
        {/* Show sources for assistant messages */}
        {isAssistant && !isStreaming && sources.length > 0 && (
          <SourcesPanel sources={sources} />
        )}
      </div>
    </div>
  );
}