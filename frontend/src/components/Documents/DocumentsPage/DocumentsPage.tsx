import { useState, useCallback, useRef } from 'react';
import { useDocuments } from '@/hooks/useDocuments';
import { DOCUMENT_STATUS_LABELS, DOCUMENT_STATUS_COLORS } from '@/constants/ui';
import './DocumentsPage.scss';

interface DocumentsPageProps {
  onError?: (error: Error) => void;
}

export function DocumentsPage({ onError }: DocumentsPageProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    documents,
    isLoading,
    uploadDocument,
    deleteDocument,
    refresh,
  } = useDocuments({ onError });

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    const files = Array.from(e.dataTransfer.files).filter(
      (file) => file.type === 'application/pdf'
    );

    if (files.length === 0) {
      onError?.(new Error('Please upload PDF files only'));
      return;
    }

    await handleUpload(files);
  }, []);

  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files) : [];
    if (files.length > 0) {
      await handleUpload(files);
    }
    // Reset input so the same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  const handleUploadClick = useCallback(() => {
    // Programmatically click the hidden file input
    fileInputRef.current?.click();
  }, []);

  const handleUpload = async (files: File[]) => {
    setIsUploading(true);
    try {
      for (const file of files) {
        await uploadDocument(file);
      }
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (id: string, filename: string) => {
    if (!confirm(`Delete "${filename}"?`)) return;
    
    try {
      await deleteDocument(id);
    } catch (error) {
      console.error('Delete failed:', error);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <div className="documents-page">
      <div className="documents-page__header">
        <h1 className="documents-page__title">Documents</h1>
        <p className="documents-page__subtitle">
          Upload and manage your PDF documents for RAG processing
        </p>
      </div>

      {/* Upload Zone */}
      <div
        className={`documents-page__upload ${isDragOver ? 'documents-page__upload--dragover' : ''} ${isUploading ? 'documents-page__upload--uploading' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleUploadClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          multiple
          onChange={handleFileSelect}
          className="documents-page__upload-input"
          style={{ display: 'none' }}
        />
        
        <div className="documents-page__upload-icon">
          {isUploading ? (
            <svg className="documents-page__spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
              <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          )}
        </div>
        
        <div className="documents-page__upload-text">
          {isUploading ? (
            <span>Uploading...</span>
          ) : (
            <>
              <span className="documents-page__upload-primary">
                Click to upload or drag and drop
              </span>
              <span className="documents-page__upload-secondary">
                PDF files only (max 50MB)
              </span>
            </>
          )}
        </div>
      </div>

      {/* Document List */}
      <div className="documents-page__list">
        <div className="documents-page__list-header">
          <h2 className="documents-page__list-title">
            Uploaded Documents
            {documents.length > 0 && (
              <span className="documents-page__list-count">{documents.length}</span>
            )}
          </h2>
          <button 
            className="documents-page__refresh-btn"
            onClick={refresh}
            disabled={isLoading}
            title="Refresh"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="23 4 23 10 17 10" />
              <polyline points="1 20 1 14 7 14" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
          </button>
        </div>

        {isLoading && documents.length === 0 ? (
          <div className="documents-page__empty">
            <div className="documents-page__loading-spinner" />
            <span>Loading documents...</span>
          </div>
        ) : documents.length === 0 ? (
          <div className="documents-page__empty">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            <span>No documents uploaded yet</span>
          </div>
        ) : (
          <ul className="documents-page__items">
            {documents.map((doc) => (
              <li key={doc.id} className="documents-page__item">
                <div className="documents-page__item-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                </div>
                
                <div className="documents-page__item-info">
                  <span className="documents-page__item-name" title={doc.original_filename}>
                    {doc.original_filename}
                  </span>
                  <span className="documents-page__item-meta">
                    {formatFileSize(doc.file_size_bytes)} • {formatDate(doc.created_at)}
                    {doc.page_count && ` • ${doc.page_count} pages`}
                  </span>
                </div>
                
                <div 
                  className="documents-page__item-status"
                  style={{ 
                    backgroundColor: `${DOCUMENT_STATUS_COLORS[doc.status]}20`,
                    color: DOCUMENT_STATUS_COLORS[doc.status]
                  }}
                >
                  {DOCUMENT_STATUS_LABELS[doc.status] || doc.status}
                </div>
                
                <button
                  className="documents-page__item-delete"
                  onClick={() => handleDelete(doc.id, doc.original_filename)}
                  title="Delete document"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}