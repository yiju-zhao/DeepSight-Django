// Conference Types
export interface Session {
  id: string;
  instance: Instance;
  instance_id: number;
  date: string;
  start_time: string;
  end_time: string;
  type: string;
  title: string;
  url: string;
  speaker?: string;
  abstract?: string;
  overview?: string;
  transcript?: string;
}

export interface Event {
  id: number;
  name: string;
  type: string;
  description: string;
}

export interface Venue {
  id: number;
  name: string;
  type: string;
  description: string;
}

export interface Instance {
  instance_id: number;
  venue: Venue;
  year: number;
  start_date: string;
  end_date: string;
  location: string;
  website: string;
  summary: string;
}

export interface Publication {
  id: string;
  instance: Instance;
  title: string;
  authors: string;
  aff: string;
  aff_unique?: string;
  aff_country_unique?: string;
  author_position?: string;
  author_homepage?: string;
  abstract: string;
  summary: string;
  session?: string;
  rating?: number;
  keywords: string;
  research_topic: string;
  tag: string;
  external_id?: string;
  doi: string;
  pdf_url: string;
  github?: string;
  site?: string;
  raw_file?: string;
}

export interface PublicationTableItem {
  id: string;
  title: string;
  authors: string;
  rating?: number;
  research_topic: string;
  session?: string;
  aff_unique?: string;
  aff_country_unique?: string;
  keywords: string;
  pdf_url: string;
  github?: string;
  site?: string;
  instance_year: number;
  venue_name: string;
}

export interface KPIData {
  total_publications: number;
  unique_authors: number;
  unique_affiliations: number;
  unique_countries: number;
  avg_rating: number;
  session_distribution: Record<string, number>;
  author_position_distribution: Record<string, number>;
  resource_counts: {
    with_github: number;
    with_site: number;
    with_pdf: number;
  };
}

export interface ChartDataItem {
  name: string;
  count: number;
  [key: string]: any; // Allow additional properties for Recharts compatibility
}

export interface RatingHistogramItem {
  rating: number;
  count: number;
}


export interface ForceGraphData {
  nodes: Array<{ id: string; val: number; group: number }>;
  links: Array<{ source: string; target: string; value: number }>;
}

export interface FineHistogramBin {
  bin: number;
  start: number;
  end: number;
  count: number;
}

export interface TreemapData {
  name: string;
  value: number;
}

export interface OrganizationPublicationData {
  organization: string;
  total: number;
  research_areas: { [area: string]: number };
}

export interface OrganizationPublicationByResearchAreaData {
  organization: string;
  [researchArea: string]: string | number; // Dynamic research area fields
}

export interface ChartData {
  topics: ChartDataItem[];
  top_affiliations: ChartDataItem[];
  top_countries: ChartDataItem[];
  top_keywords: ChartDataItem[];
  ratings_histogram: RatingHistogramItem[];
  session_types: ChartDataItem[];
  author_positions: ChartDataItem[];
  // New visualizations
  force_graphs: {
    country: ForceGraphData;
    organization: ForceGraphData;
  };
  ratings_histogram_fine: FineHistogramBin[];
  keywords_treemap: TreemapData[];
  organization_publications: OrganizationPublicationData[];
  organization_publications_by_research_area: OrganizationPublicationByResearchAreaData[];
}

export interface PaginationInfo {
  count: number;
  next?: string | null;
  previous?: string | null;
}

export interface DashboardResponse {
  kpis: KPIData;
  charts: ChartData;
  table: PublicationTableItem[];
  pagination: PaginationInfo;
}

export interface ConferenceOverview {
  total_conferences: number;
  total_papers: number;
  years_covered: number[];
  avg_papers_per_year: number;
  conferences: {
    name: string;
    type: string;
    instances: number;
    total_papers: number;
    years: number[];
  }[];
}

export interface PaginatedResponse<T> {
  count: number;
  next?: string;
  previous?: string;
  results: T[];
}

// Dashboard query parameters
export interface DashboardParams {
  venue?: string;
  year?: number;
  instance?: number;
  page?: number;
  page_size?: number;
  bin_size?: number;
}

export interface InstanceParams {
  venue?: string;
}

// Import to Notebook Types
export interface ImportToNotebookRequest {
  publication_ids: string[];
  action: "add" | "create";
  notebook_id?: string;
  notebook_name?: string;
}

export interface SkippedItem {
  publication_id: string;
  title: string;
  reason: string;
  existing_item_id?: string;
}

export interface ImportedItem {
  publication_id: string;
  title: string;
  kb_item_id: string;
  url: string;
}

export interface FailedItem {
  publication_id: string;
  title: string;
  url: string;
  reason: string;
}

export interface ImportResponse {
  success: boolean;
  total_requested: number;
  imported: number;
  failed: number;
  skipped: number;
  skipped_no_url: SkippedItem[];
  skipped_duplicate: SkippedItem[];
  successful_imports: ImportedItem[];
  failed_imports: FailedItem[];
  batch_job_id: string | null;
  appended_to_batch: boolean;
  message: string;
  notebook_id?: string;
  notebook_name?: string;
}

export interface ActiveImport {
  batch_job_id: string;
  notebook_id: string;
  notebook_name: string;
  status: "pending" | "processing" | "completed" | "failed" | "partially_completed";
  total_items: number;
  completed_items: number;
  failed_items: number;
  progress_percentage: number;
  created_at: string;
  updated_at: string;
}