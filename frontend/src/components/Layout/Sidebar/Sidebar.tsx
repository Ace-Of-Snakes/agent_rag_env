import { useState, useEffect, useRef, useCallback } from 'react';
import { chatApi } from '@/services/api';
import type { Chat } from '@/types';
import './Sidebar.scss';

type ViewType = 'chats' | 'documents';

interface SidebarProps {
  isOpen: boolean;
  currentChatId: string | null;
  currentView: ViewType;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
  onViewChange: (view: ViewType) => void;
  onClearChat?: () => void; // New: just clear selection, don't create new
}

export function Sidebar({
  isOpen,
  currentChatId,
  currentView,
  onSelectChat,
  onNewChat,
  onViewChange,
  onClearChat,
}: SidebarProps) {
  const [chats, setChats] = useState<Chat[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [editingChatId, setEditingChatId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Load chats on mount
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

  // Only reload when a NEW chat is created (not on delete)
  // Check if currentChatId exists and isn't in our list
  useEffect(() => {
    if (currentChatId && chats.length > 0 && !chats.find(c => c.id === currentChatId)) {
      // This is likely a newly created chat, reload the list
      loadChats();
    }
  }, [currentChatId]);

  const handleDeleteChat = async (e: React.MouseEvent, chatId: string) => {
    e.stopPropagation();
    if (!confirm('Delete this chat?')) return;

    try {
      await chatApi.delete(chatId);
      
      // Remove from local state immediately
      setChats((prev) => prev.filter((c) => c.id !== chatId));
      
      // If this was the current chat, just clear the selection
      // DON'T create a new chat - let user do that manually
      if (currentChatId === chatId) {
        onClearChat?.();
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
    setTimeout(() => {
      if (editingChatId) {
        handleRenameSubmit();
      }
    }, 100);
  };

  const handleNavClick = (view: ViewType) => {
    onViewChange(view);
  };

  return (
    <aside className={`sidebar ${isOpen ? 'sidebar--open' : 'sidebar--collapsed'}`}>
      {/* Icon Rail - Always visible */}
      <div className="sidebar__rail">
        <div className="sidebar__rail-logo">R</div>
        
        <nav className="sidebar__rail-nav">
          <button
            className={`sidebar__rail-btn ${currentView === 'chats' ? 'active' : ''}`}
            onClick={() => handleNavClick('chats')}
            title="Chats"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </button>
          
          <button
            className={`sidebar__rail-btn ${currentView === 'documents' ? 'active' : ''}`}
            onClick={() => handleNavClick('documents')}
            title="Documents"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
          </button>
        </nav>
      </div>

      {/* Expandable Panel */}
      <div className="sidebar__panel">
        <div className="sidebar__header">
          <h1 className="sidebar__logo">RAGent</h1>
        </div>

        {currentView === 'chats' && (
          <div className="sidebar__content">
            <div className="sidebar__section-header">
              <h3 className="sidebar__section-title">Chats</h3>
              <button className="sidebar__new-btn" onClick={onNewChat} title="New Chat">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
              </button>
            </div>
            
            <div className="sidebar__list">
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
                              className="sidebar__chat-action"
                              onClick={(e) => handleStartRename(e, chat)}
                              aria-label="Rename chat"
                              title="Rename"
                            >
                              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                              </svg>
                            </button>
                            <button
                              className="sidebar__chat-action sidebar__chat-action--delete"
                              onClick={(e) => handleDeleteChat(e, chat.id)}
                              aria-label="Delete chat"
                              title="Delete"
                            >
                              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <polyline points="3 6 5 6 21 6" />
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                                <line x1="10" y1="11" x2="10" y2="17" />
                                <line x1="14" y1="11" x2="14" y2="17" />
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
          </div>
        )}

        {currentView === 'documents' && (
          <div className="sidebar__content">
            <div className="sidebar__section-header">
              <h3 className="sidebar__section-title">Documents</h3>
            </div>
            <div className="sidebar__nav-hint">
              View and manage documents in the main panel
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}