import { ThemeToggle } from '@/components/common';
import './Header.scss';

interface HeaderProps {
  title?: string;
  theme: 'light' | 'dark';
  onToggleSidebar?: () => void;
  onToggleTheme?: () => void;
}

export function Header({ 
  title = 'RAGent', 
  theme,
  onToggleSidebar, 
  onToggleTheme 
}: HeaderProps) {
  return (
    <header className="header">
      <div className="header__left">
        <button className="header__menu-btn" onClick={onToggleSidebar} aria-label="Toggle sidebar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 12h18M3 6h18M3 18h18" />
          </svg>
        </button>
        <h1 className="header__title">{title}</h1>
      </div>
      <div className="header__right">
        <ThemeToggle theme={theme} onToggle={onToggleTheme || (() => {})} />
      </div>
    </header>
  );
}