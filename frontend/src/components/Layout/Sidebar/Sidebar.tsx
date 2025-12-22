import { useState, useEffect, useRef, useCallback } from 'react';
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
  const [editingChatId, setEditingChatId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadChats();
  }, []);

  // Focus input when editing starts
  useEffect(() => {
    if (editingChatId && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingChatId]);

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

  // Refresh chats when a new chat might have been created
  useEffect(() => {
    if (currentChatId && !chats.find(c => c.id === currentChatId)) {
      loadChats();
    }
  }, [currentChatId, chats]);

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

  const handleStartRename = (e: React.MouseEvent, chat: Chat) => {
    e.stopPropagation();
    setEditingChatId(chat.id);
    setEditTitle(chat.title || 'New Chat');
  };

  const handleRenameSubmit = useCallback(async () => {
    if (!editingChatId || !editTitle.trim()) {
      setEditingChatId(null);
      return;
    }

    try {
      const updatedChat = await chatApi.updateTitle(editingChatId, editTitle.trim());
      setChats((prev) =>
        prev.map((c) => (c.id === editingChatId ? { ...c, title: updatedChat.title } : c))
      );
    } catch (error) {
      console.error('Failed to rename chat:', error);
    } finally {
      setEditingChatId(null);
    }
  }, [editingChatId, editTitle]);

  const handleRenameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleRenameSubmit();
    } else if (e.key === 'Escape') {
      setEditingChatId(null);
    }
  };

  const handleRenameBlur = () => {
    // Small delay to allow click events to fire first
    setTimeout(() => {
      if (editingChatId) {
        handleRenameSubmit();
      }
    }, 100);
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
                onClick={() => !editingChatId && onSelectChat(chat.id)}
              >
                {editingChatId === chat.id ? (
                  <input
                    ref={inputRef}
                    type="text"
                    className="sidebar__chat-rename-input"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onKeyDown={handleRenameKeyDown}
                    onBlur={handleRenameBlur}
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <>
                    <span 
                      className="sidebar__chat-title"
                      onDoubleClick={(e) => handleStartRename(e, chat)}
                      title="Double-click to rename"
                    >
                      {chat.title || 'New Chat'}
                    </span>
                    <div className="sidebar__chat-actions">
                      <button
                        className="sidebar__chat-rename"
                        onClick={(e) => handleStartRename(e, chat)}
                        aria-label="Rename chat"
                        title="Rename chat"
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                        </svg>
                      </button>
                      <button
                        className="sidebar__chat-delete"
                        onClick={(e) => handleDeleteChat(e, chat.id)}
                        aria-label="Delete chat"
                        title="Delete chat"
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M18 6L6 18M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}