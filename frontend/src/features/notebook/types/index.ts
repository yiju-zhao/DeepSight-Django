/**
 * Notebook Feature Types - Barrel Export
 * 
 * Re-exports all types used within the notebook feature from their respective modules.
 */

// UI Component Props and Feature-specific types
export * from './ui';

// Agent types for RAG agent state visualization
export * from './agent';

// Note types for notes feature
export * from './note';

// Studio item types (reports, podcasts, notes unified)
export * from './studioItem';

// Re-export shared domain types for convenience
export type {
    Notebook,
    CreateNotebookRequest,
    UpdateNotebookRequest,
    NotebookStats,
    GetNotebooksParams,
    OrderingField,
    Source,
    CreateSourceRequest,
    UpdateSourceRequest,
    ProcessUrlRequest,
    AddTextRequest,
    ChatMessage,
    ChatResponse as SharedChatResponse,
    KnowledgeBaseItem,
    KnowledgeBaseImage,
} from '@/shared/types/notebook';
