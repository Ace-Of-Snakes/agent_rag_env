import { useChat } from '@/hooks/useChat';
import { MessageList } from '../MessageList/MessageList';
import { InputArea } from '../InputArea/InputArea';
import { Spinner } from '@/components/common';
import './ChatContainer.scss';

interface ChatContainerProps {
  chatId: string | null;
  onError?: (error: Error) => void;
}

export function ChatContainer({ chatId, onError }: ChatContainerProps) {
  const {
    messages,
    isLoading,
    streaming,
    sendMessage,
    cancelStreaming,
  } = useChat(chatId, { onError });

  if (isLoading) {
    return (
      <div className="chat-container chat-container--loading">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="chat-container">
      <MessageList
        messages={messages}
        streamingContent={streaming.currentResponse}
        isStreaming={streaming.isStreaming}
      />
      
      {streaming.currentTool && (
        <div className="chat-container__tool-indicator">
          <Spinner size="sm" />
          <span>Using {streaming.currentTool}...</span>
        </div>
      )}
      
      <InputArea
        onSend={sendMessage}
        onCancel={cancelStreaming}
        isStreaming={streaming.isStreaming}
        disabled={!chatId}
        placeholder={chatId ? 'Type a message...' : 'Create a new chat to start'}
      />
    </div>
  );
}
