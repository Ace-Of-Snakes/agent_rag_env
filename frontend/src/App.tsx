import { useState, useCallback } from 'react';
import { Header } from './components/Layout/Header/Header';
import { Sidebar } from './components/Layout/Sidebar/Sidebar';
import { ChatContainer } from './components/Chat/ChatContainer/ChatContainer';
import { chatApi } from './services/api';
import './App.scss';

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleNewChat = useCallback(async () => {
    try {
      const chat = await chatApi.create({});
      setCurrentChatId(chat.id);
    } catch (err) {
      setError('Failed to create new chat');
      console.error(err);
    }
  }, []);

  const handleSelectChat = useCallback((chatId: string) => {
    setCurrentChatId(chatId);
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
        onNewChat={handleNewChat}
      />
      
      <div className="app__body">
        <Sidebar
          isOpen={sidebarOpen}
          currentChatId={currentChatId}
          onSelectChat={handleSelectChat}
          onNewChat={handleNewChat}
        />
        
        <main className={`app__main ${sidebarOpen ? '' : 'app__main--expanded'}`}>
          <ChatContainer
            chatId={currentChatId}
            onError={handleError}
          />
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
