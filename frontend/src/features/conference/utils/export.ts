/**
 * Data Export Utilities
 *
 * Provides functions to export conference publication data in various formats.
 * Supports CSV and JSON exports with customizable field selection.
 */

import Papa from 'papaparse';
import { Publication } from '../types';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export type ExportFormat = 'csv' | 'json';

export interface ExportField {
  key: keyof Publication | string;
  label: string;
  transform?: (value: any, publication: Publication) => string | number;
}

export interface ExportOptions {
  format: ExportFormat;
  fields?: ExportField[];
  filename?: string;
  includeHeaders?: boolean;
}

// ============================================================================
// DEFAULT EXPORT FIELDS
// ============================================================================

/**
 * Default fields included in exports
 */
export const DEFAULT_EXPORT_FIELDS: ExportField[] = [
  { key: 'title', label: 'Title' },
  {
    key: 'authors',
    label: 'Authors',
    transform: (value) => (Array.isArray(value) ? value.join('; ') : value),
  },
  {
    key: 'aff',
    label: 'Affiliations',
    transform: (value) => (Array.isArray(value) ? value.join('; ') : value),
  },
  {
    key: 'aff_country_unique',
    label: 'Countries',
    transform: (value) => (Array.isArray(value) ? value.join('; ') : value),
  },
  { key: 'rating', label: 'Rating' },
  { key: 'research_topic', label: 'Research Topic' },
  {
    key: 'keywords',
    label: 'Keywords',
    transform: (value) => (Array.isArray(value) ? value.join('; ') : value),
  },
  { key: 'session', label: 'Session' },
  { key: 'abstract', label: 'Abstract' },
  { key: 'pdf_url', label: 'PDF URL' },
  { key: 'github', label: 'GitHub URL' },
  { key: 'site', label: 'Website URL' },
  { key: 'doi', label: 'DOI' },
];

/**
 * All available fields for export with transformations
 */
export const ALL_EXPORT_FIELDS: ExportField[] = [
  ...DEFAULT_EXPORT_FIELDS,
  {
    key: 'aff_unique',
    label: 'Unique Affiliations',
    transform: (value) => (Array.isArray(value) ? value.join('; ') : value),
  },
  { key: 'summary', label: 'Summary' },
  {
    key: 'id',
    label: 'ID',
    transform: (value) => String(value),
  },
];

// ============================================================================
// EXPORT FUNCTIONS
// ============================================================================

/**
 * Transform publication data according to field definitions
 */
function transformData(
  publications: Publication[],
  fields: ExportField[]
): Record<string, any>[] {
  return publications.map((publication) => {
    const row: Record<string, any> = {};

    fields.forEach((field) => {
      const value = (publication as any)[field.key];
      row[field.label] = field.transform
        ? field.transform(value, publication)
        : value ?? '';
    });

    return row;
  });
}

/**
 * Export publications to CSV format
 */
export function exportToCSV(
  publications: Publication[],
  fields: ExportField[] = DEFAULT_EXPORT_FIELDS,
  filename: string = 'publications.csv'
): void {
  try {
    // Transform data
    const transformedData = transformData(publications, fields);

    // Generate CSV
    const csv = Papa.unparse(transformedData, {
      quotes: true,
      quoteChar: '"',
      escapeChar: '"',
      delimiter: ',',
      header: true,
      newline: '\n',
    });

    // Create blob and download
    downloadFile(csv, filename, 'text/csv;charset=utf-8;');
  } catch (error) {
    console.error('Failed to export CSV:', error);
    throw new Error('Failed to export data as CSV. Please try again.');
  }
}

/**
 * Export publications to JSON format
 */
export function exportToJSON(
  publications: Publication[],
  fields: ExportField[] = DEFAULT_EXPORT_FIELDS,
  filename: string = 'publications.json'
): void {
  try {
    // Transform data
    const transformedData = transformData(publications, fields);

    // Generate JSON with formatting
    const json = JSON.stringify(transformedData, null, 2);

    // Create blob and download
    downloadFile(json, filename, 'application/json;charset=utf-8;');
  } catch (error) {
    console.error('Failed to export JSON:', error);
    throw new Error('Failed to export data as JSON. Please try again.');
  }
}

/**
 * Export publications in specified format
 */
export function exportPublications(
  publications: Publication[],
  options: ExportOptions
): void {
  const {
    format,
    fields = DEFAULT_EXPORT_FIELDS,
    filename,
  } = options;

  if (!publications || publications.length === 0) {
    throw new Error('No publications to export');
  }

  const defaultFilename = `publications-${new Date().toISOString().split('T')[0]}`;

  switch (format) {
    case 'csv':
      exportToCSV(
        publications,
        fields,
        filename || `${defaultFilename}.csv`
      );
      break;

    case 'json':
      exportToJSON(
        publications,
        fields,
        filename || `${defaultFilename}.json`
      );
      break;

    default:
      throw new Error(`Unsupported export format: ${format}`);
  }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Trigger browser download for a file
 */
function downloadFile(
  content: string,
  filename: string,
  mimeType: string
): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.style.display = 'none';

  document.body.appendChild(link);
  link.click();

  // Cleanup
  setTimeout(() => {
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, 100);
}

/**
 * Get export field by key
 */
export function getExportField(key: string): ExportField | undefined {
  return ALL_EXPORT_FIELDS.find((field) => field.key === key);
}

/**
 * Create custom export fields configuration
 */
export function createExportFields(keys: string[]): ExportField[] {
  return keys
    .map((key) => getExportField(key))
    .filter((field): field is ExportField => field !== undefined);
}

/**
 * Estimate export file size in bytes
 */
export function estimateFileSize(
  publications: Publication[],
  format: ExportFormat,
  fields: ExportField[] = DEFAULT_EXPORT_FIELDS
): number {
  if (!publications.length) return 0;

  // Sample first publication
  const sample = transformData([publications[0]], fields);
  const sampleStr =
    format === 'csv'
      ? Papa.unparse(sample)
      : JSON.stringify(sample, null, 2);

  const avgBytesPerRow = new Blob([sampleStr]).size;
  const estimatedTotal = avgBytesPerRow * publications.length;

  return estimatedTotal;
}

/**
 * Format file size for display
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Validate export options
 */
export function validateExportOptions(
  options: ExportOptions
): { valid: boolean; error?: string } {
  if (!options.format) {
    return { valid: false, error: 'Export format is required' };
  }

  if (!['csv', 'json'].includes(options.format)) {
    return { valid: false, error: 'Invalid export format' };
  }

  if (options.fields && options.fields.length === 0) {
    return { valid: false, error: 'At least one field must be selected' };
  }

  return { valid: true };
}

// ============================================================================
// EXPORT DEFAULTS
// ============================================================================

export default {
  exportPublications,
  exportToCSV,
  exportToJSON,
  DEFAULT_EXPORT_FIELDS,
  ALL_EXPORT_FIELDS,
  createExportFields,
  getExportField,
  estimateFileSize,
  formatFileSize,
  validateExportOptions,
};
