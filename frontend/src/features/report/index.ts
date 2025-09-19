export { default as ReportPage } from './pages/ReportPage';
export { default as ResearchReport } from './pages/ResearchReport';
export {
  ReportCard,
  ReportDetail,
  ReportEditor,
  ReportFilters as ReportFiltersComponent,
  ReportList,
  ReportListItem,
  ReportStats as ReportStatsComponent
} from './components';

// Export React Query hooks with specific names to avoid conflicts
export {
  useReportsList,
  useReport,
  useReportContent,
  useReportModels,
  useCreateReport,
  useUpdateReport,
  useCancelReport,
  useDeleteReport,
  useReportsUtils,
  // Export types with 'Query' suffix to distinguish from legacy types
  type Report as QueryReport,
  type ReportListResponse,
  type ReportContentResponse,
  type ReportGenerationRequest as QueryReportGenerationRequest,
  type CreateReportResponse,
} from './hooks/useReports';

export * from './services/ReportService';

// Export legacy types (these will be the main ones used in the app)
export * from './types/type';