import { Button } from '@/components/common';
import { DOCUMENT_STATUS_LABELS, DOCUMENT_STATUS_COLORS } from '@/constants/ui';
import type { Document } from '@/types';
import './DocumentCard.scss';

interface DocumentCardProps {
  document: Document;
  onDelete: (id: string) => void;
  onClick?: (id: string) => void;
}

export function DocumentCard({ document, onDelete, onClick }: DocumentCardProps) {
  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <div
      className="document-card"
      onClick={() => onClick?.(document.id)}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      <div className="document-card__icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
      </div>

      <div className="document-card__content">
        <h3 className="document-card__title">{document.original_filename}</h3>
        
        <div className="document-card__meta">
          <span className="document-card__size">{formatBytes(document.file_size_bytes)}</span>
          <span className="document-card__date">{formatDate(document.created_at)}</span>
          {document.page_count && (
            <span className="document-card__pages">{document.page_count} pages</span>
          )}
        </div>

        {document.summary && (
          <p className="document-card__summary">{document.summary}</p>
        )}
      </div>

      <div className="document-card__status">
        <span
          className="document-card__status-badge"
          style={{ backgroundColor: DOCUMENT_STATUS_COLORS[document.status] }}
        >
          {DOCUMENT_STATUS_LABELS[document.status]}
        </span>
      </div>

      <div className="document-card__actions">
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            onDelete(document.id);
          }}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
        </Button>
      </div>
    </div>
  );
}
