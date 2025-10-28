// Shared notebook domain types (single source of truth)

export interface Notebook {
  readonly id: string;
  readonly created_at: string;
  readonly updated_at: string;
  name: string;
  description: string;
  // Aggregates (optional depending on endpoint)
  source_count?: number;
  knowledge_item_count?: number;
  chat_message_count?: number;
  last_activity?: string;
  ragflow_dataset_info?: any;
  // Legacy/optional fields
  user?: string;
  isPublic?: boolean;
  tags?: string[];
}

export interface CreateNotebookRequest {
  name: string;
  description?: string;
}

export interface UpdateNotebookRequest {
  name?: string;
  description?: string;
}

export interface NotebookStats {
  sourceCount: number;
  itemCount: number;
  processingCount: number;
  lastUpdated: string;
}

export type OrderingField =
  | 'name'
  | '-name'
  | 'created_at'
  | '-created_at'
  | 'updated_at'
  | '-updated_at';

export interface GetNotebooksParams {
  page?: number;
  pageSize?: number;
  search?: string;
  ordering?: OrderingField;
}

// Sources
export interface Source {
  readonly id: string;
  readonly createdAt?: string;
  readonly updatedAt?: string;
  name?: string;
  sourceType: 'file' | 'url' | 'text';
  status?: 'pending' | 'processing' | 'completed' | 'failed';
  metadata?: Record<string, any>;
}

export interface CreateSourceRequest {
  name?: string;
  sourceType: 'file' | 'url' | 'text';
}

export interface UpdateSourceRequest {
  name?: string;
}

export interface ProcessUrlRequest {
  url: string;
  includeImages?: boolean;
  includeDocuments?: boolean;
}

export interface AddTextRequest {
  title: string;
  content: string;
}

// Chat
export interface ChatMessage {
  readonly id: string;
  readonly createdAt: string;
  message: string;
  response?: string;
  isUser: boolean;
}

export interface ChatResponse {
  id: string;
  message: string;
  response: string;
}

// Knowledge base
export interface KnowledgeBaseItem {
  readonly id: string;
  readonly createdAt: string;
  title: string;
  content: string;
  sourceId: string;
}

export interface KnowledgeBaseImage {
  readonly id: string;
  filename: string;
  url: string;
  caption?: string;
}

