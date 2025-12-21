import { useState, useRef, useCallback, KeyboardEvent } from 'react';
import { Button } from '@/components/common';
import './InputArea.scss';

interface InputAreaProps {
  onSend: (content: string) => void;
  onCancel?: () => void;
  isStreaming?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export function InputArea({
  onSend,
  onCancel,
  isStreaming,
  disabled,
  placeholder = 'Type a message...',
}: InputAreaProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled || isStreaming) return;

    onSend(trimmed);
    setValue('');

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [value, disabled, isStreaming, onSend]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  };

  return (
    <div className="input-area">
      <div className="input-area__container">
        <textarea
          ref={textareaRef}
          className="input-area__input"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
        />
        
        <div className="input-area__actions">
          {isStreaming ? (
            <Button
              variant="secondary"
              size="sm"
              onClick={onCancel}
            >
              Stop
            </Button>
          ) : (
            <Button
              variant="primary"
              size="sm"
              onClick={handleSubmit}
              disabled={!value.trim() || disabled}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
              </svg>
            </Button>
          )}
        </div>
      </div>
      
      <p className="input-area__hint">
        Press Enter to send, Shift+Enter for new line
      </p>
    </div>
  );
}
