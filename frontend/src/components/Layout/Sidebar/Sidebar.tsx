import { useState, useEffect } from 'react';
import { Button } from '@/components/common';
import { chatApi } from '@/services/api';
import type { Chat } from '@/types';
import './Sidebar.scss';

interface SidebarProps {
  isOpen: boolean;
  currentChatId: string | null;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
}

export function Sidebar({
  isOpen,
  currentChatId,
  onSelectChat,
  onNewChat,
}: SidebarProps) {
  const [chats, setChats] = useState<Chat[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadChats();
  }, []);

  const loadChats = async () => {
    setIsLoading(true);
    try {
      const response = await chatApi.list(1, 50);
      setChats(response.chats);
    } catch (error) {
      console.error('Failed to load chats:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteChat = async (e: React.MouseEvent, chatId: string) => {
    e.stopPropagation();
    if (!confirm('Delete this chat?')) return;

    try {
      await chatApi.delete(chatId);
      setChats((prev) => prev.filter((c) => c.id !== chatId));
      if (currentChatId === chatId) {
        onNewChat();
      }
    } catch (error) {
      console.error('Failed to delete chat:', error);
    }
  };

  return (
    <aside className={`sidebar ${isOpen ? 'sidebar--open' : ''}`}>
      <div className="sidebar__header">
        <h1 className="sidebar__logo">RAGent</h1>
        <Button variant="primary" size="sm" onClick={onNewChat}>
          + New Chat
        </Button>
      </div>

      <div className="sidebar__chats">
        <h3 className="sidebar__section-title">Recent Chats</h3>
        {isLoading ? (
          <div className="sidebar__loading">Loading...</div>
        ) : chats.length === 0 ? (
          <div className="sidebar__empty">No chats yet</div>
        ) : (
          <ul className="sidebar__chat-list">
            {chats.map((chat) => (
              <li
                key={chat.id}
                className={`sidebar__chat-item ${chat.id === currentChatId ? 'active' : ''}`}
                onClick={() => onSelectChat(chat.id)}
              >
                <span className="sidebar__chat-title">
                  {chat.title || 'New Chat'}
                </span>
                <button
                  className="sidebar__chat-delete"
                  onClick={(e) => handleDeleteChat(e, chat.id)}
                  aria-label="Delete chat"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M18 6L6 18M6 6l12 12" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
