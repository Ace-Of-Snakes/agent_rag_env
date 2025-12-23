import { useState, useCallback } from 'react';
import { Header } from './components/Layout/Header/Header';
import { Sidebar } from './components/Layout/Sidebar/Sidebar';
import { ChatContainer } from './components/Chat/ChatContainer/ChatContainer';
import { DocumentsPage } from './components/Documents/DocumentsPage/DocumentsPage';
import { chatApi } from './services/api';
import { useTheme } from './hooks/useTheme';
import './App.scss';

type ViewType = 'chats' | 'documents';

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [currentView, setCurrentView] = useState<ViewType>('chats');
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { theme, toggleTheme } = useTheme();

  const handleNewChat = useCallback(async () => {
    try {
      const chat = await chatApi.create({});
      setCurrentChatId(chat.id);
      setCurrentView('chats');
    } catch (err) {
      setError('Failed to create new chat');
      console.error(err);
    }
  }, []);

  const handleSelectChat = useCallback((chatId: string) => {
    setCurrentChatId(chatId);
    setCurrentView('chats');
  }, []);

  const handleViewChange = useCallback((view: ViewType) => {
    setCurrentView(view);
  }, []);

  const handleError = useCallback((err: Error) => {
    setError(err.message);
    setTimeout(() => setError(null), 5000);
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebarOpen((prev) => !prev);
  }, []);

  return (
    <div className="app">
      <Header 
        onToggleSidebar={toggleSidebar} 
        theme={theme}
        onToggleTheme={toggleTheme}
      />
      
      <div className="app__body">
        <Sidebar
          isOpen={sidebarOpen}
          currentChatId={currentChatId}
          currentView={currentView}
          onSelectChat={handleSelectChat}
          onNewChat={handleNewChat}
          onViewChange={handleViewChange}
        />
        
        <main className="app__main">
          {currentView === 'chats' && (
            <ChatContainer
              chatId={currentChatId}
              onError={handleError}
            />
          )}
          {currentView === 'documents' && (
            <DocumentsPage onError={handleError} />
          )}
        </main>
      </div>

      {error && (
        <div className="app__error">
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}
    </div>
  );
}

export default App;