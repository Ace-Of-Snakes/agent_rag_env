import { useState, useCallback, useEffect } from 'react';
import { documentApi } from '@/services/api';
import type { Document, DocumentStatus, SearchResult } from '@/types';

interface UseDocumentsOptions {
  autoLoad?: boolean;
  pageSize?: number;
  onError?: (error: Error) => void;
}

export function useDocuments(options: UseDocumentsOptions = {}) {
  const { autoLoad = true, pageSize = 20, onError } = options;

  // State
  const [documents, setDocuments] = useState<Document[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<DocumentStatus | undefined>();

  // Load documents
  const loadDocuments = useCallback(
    async (pageNum = 1, status?: DocumentStatus) => {
      setIsLoading(true);
      try {
        const response = await documentApi.list(pageNum, pageSize, status);
        setDocuments(response.documents);
        setTotal(response.total);
        setPage(pageNum);
      } catch (error) {
        onError?.(error as Error);
      } finally {
        setIsLoading(false);
      }
    },
    [pageSize, onError]
  );

  // Auto-load on mount
  useEffect(() => {
    if (autoLoad) {
      loadDocuments(1, statusFilter);
    }
  }, [autoLoad, statusFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  // Upload document
  const uploadDocument = useCallback(
    async (file: File) => {
      try {
        const response = await documentApi.upload(file);
        // Reload documents to include the new one
        await loadDocuments(1, statusFilter);
        return response;
      } catch (error) {
        onError?.(error as Error);
        throw error;
      }
    },
    [loadDocuments, statusFilter, onError]
  );

  // Delete document
  const deleteDocument = useCallback(
    async (id: string) => {
      try {
        await documentApi.delete(id);
        // Remove from local state
        setDocuments((prev) => prev.filter((d) => d.id !== id));
        setTotal((prev) => prev - 1);
      } catch (error) {
        onError?.(error as Error);
        throw error;
      }
    },
    [onError]
  );

  // Filter by status
  const filterByStatus = useCallback((status?: DocumentStatus) => {
    setStatusFilter(status);
    setPage(1);
  }, []);

  // Pagination
  const goToPage = useCallback(
    (pageNum: number) => {
      loadDocuments(pageNum, statusFilter);
    },
    [loadDocuments, statusFilter]
  );

  const hasMore = page * pageSize < total;

  return {
    documents,
    total,
    page,
    pageSize,
    hasMore,
    isLoading,
    statusFilter,
    loadDocuments: () => loadDocuments(page, statusFilter),
    uploadDocument,
    deleteDocument,
    filterByStatus,
    goToPage,
    refresh: () => loadDocuments(1, statusFilter),
  };
}

// Hook for document search
export function useDocumentSearch(onError?: (error: Error) => void) {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchTime, setSearchTime] = useState<number | null>(null);

  const search = useCallback(
    async (query: string, topK = 5, documentIds?: string[]) => {
      if (!query.trim()) {
        setResults([]);
        return;
      }

      setIsSearching(true);
      try {
        const response = await documentApi.search(query, topK, documentIds);
        setResults(response.results);
        setSearchTime(response.search_time_ms);
      } catch (error) {
        onError?.(error as Error);
        setResults([]);
      } finally {
        setIsSearching(false);
      }
    },
    [onError]
  );

  const clearResults = useCallback(() => {
    setResults([]);
    setSearchTime(null);
  }, []);

  return {
    results,
    isSearching,
    searchTime,
    search,
    clearResults,
  };
}
