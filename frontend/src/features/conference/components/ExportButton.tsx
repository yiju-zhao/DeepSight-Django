/**
 * ExportButton Component
 *
 * Provides UI for exporting publication data in various formats.
 * Features:
 * - Format selection (CSV, JSON)
 * - Field selection (customize which fields to export)
 * - Export preview with file size estimation
 * - Batch export support
 */

import { useState } from 'react';
import { Download, FileText, FileJson, Check } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/shared/components/ui/popover';
import { Checkbox } from '@/shared/components/ui/checkbox';
import { Separator } from '@/shared/components/ui/separator';
import { Publication, PublicationTableItem } from '../types';
import {
  exportPublications,
  ExportFormat,
  ExportField,
  ExportablePublication,
  DEFAULT_EXPORT_FIELDS,
  ALL_EXPORT_FIELDS,
  estimateFileSize,
  formatFileSize,
} from '../utils/export';

interface ExportButtonProps {
  publications: ExportablePublication[];
  selectedPublications?: ExportablePublication[];
  disabled?: boolean;
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'default' | 'sm' | 'lg';
  className?: string;
}

export function ExportButton({
  publications,
  selectedPublications,
  disabled = false,
  variant = 'outline',
  size = 'default',
  className,
}: ExportButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('csv');
  const [selectedFields, setSelectedFields] = useState<string[]>(
    DEFAULT_EXPORT_FIELDS.map((f) => f.key as string)
  );
  const [isExporting, setIsExporting] = useState(false);

  // Determine which publications to export
  const dataToExport =
    selectedPublications && selectedPublications.length > 0
      ? selectedPublications
      : publications;

  const canExport = dataToExport.length > 0 && !disabled;

  // Handle field selection
  const toggleField = (fieldKey: string) => {
    setSelectedFields((prev) =>
      prev.includes(fieldKey)
        ? prev.filter((key) => key !== fieldKey)
        : [...prev, fieldKey]
    );
  };

  const toggleAllFields = () => {
    if (selectedFields.length === ALL_EXPORT_FIELDS.length) {
      setSelectedFields(DEFAULT_EXPORT_FIELDS.map((f) => f.key as string));
    } else {
      setSelectedFields(ALL_EXPORT_FIELDS.map((f) => f.key as string));
    }
  };

  // Handle export
  const handleExport = async () => {
    if (!canExport) return;

    setIsExporting(true);

    try {
      const fieldsToExport = ALL_EXPORT_FIELDS.filter((field) =>
        selectedFields.includes(field.key as string)
      );

      const filename = selectedPublications?.length
        ? `selected-publications-${new Date().toISOString().split('T')[0]}.${selectedFormat}`
        : `publications-${new Date().toISOString().split('T')[0]}.${selectedFormat}`;

      exportPublications(dataToExport, {
        format: selectedFormat,
        fields: fieldsToExport,
        filename,
      });

      // Close popover after successful export
      setTimeout(() => {
        setIsOpen(false);
      }, 500);
    } catch (error) {
      console.error('Export failed:', error);
      // TODO: Show error toast
    } finally {
      setIsExporting(false);
    }
  };

  // Calculate estimated file size
  const estimatedSize = canExport
    ? formatFileSize(
        estimateFileSize(
          dataToExport,
          selectedFormat,
          ALL_EXPORT_FIELDS.filter((field) =>
            selectedFields.includes(field.key as string)
          )
        )
      )
    : '0 Bytes';

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant={variant}
          size={size}
          className={className}
          disabled={!canExport}
        >
          <Download className="h-4 w-4 mr-2" />
          Export
          {selectedPublications && selectedPublications.length > 0 && (
            <span className="ml-1.5 text-xs bg-primary/10 text-primary px-1.5 py-0.5 rounded-full font-medium">
              {selectedPublications.length}
            </span>
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent className="w-96 p-0" align="end">
        <div className="p-4 space-y-4">
          {/* Header */}
          <div>
            <h4 className="font-semibold text-sm text-foreground">
              Export Publications
            </h4>
            <p className="text-xs text-muted-foreground mt-1">
              {dataToExport.length} publication{dataToExport.length !== 1 ? 's' : ''}{' '}
              • {estimatedSize}
            </p>
          </div>

          <Separator />

          {/* Format Selection */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Format
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => setSelectedFormat('csv')}
                className={`
                  flex items-center justify-center gap-2 px-3 py-2 rounded-md border-2 transition-all
                  ${
                    selectedFormat === 'csv'
                      ? 'border-primary bg-primary/5 text-primary'
                      : 'border-border hover:border-primary/50 hover:bg-accent'
                  }
                `}
              >
                <FileText className="h-4 w-4" />
                <span className="text-sm font-medium">CSV</span>
                {selectedFormat === 'csv' && <Check className="h-3.5 w-3.5 ml-auto" />}
              </button>

              <button
                onClick={() => setSelectedFormat('json')}
                className={`
                  flex items-center justify-center gap-2 px-3 py-2 rounded-md border-2 transition-all
                  ${
                    selectedFormat === 'json'
                      ? 'border-primary bg-primary/5 text-primary'
                      : 'border-border hover:border-primary/50 hover:bg-accent'
                  }
                `}
              >
                <FileJson className="h-4 w-4" />
                <span className="text-sm font-medium">JSON</span>
                {selectedFormat === 'json' && <Check className="h-3.5 w-3.5 ml-auto" />}
              </button>
            </div>
          </div>

          <Separator />

          {/* Field Selection */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Fields
              </label>
              <button
                onClick={toggleAllFields}
                className="text-xs text-primary hover:underline"
              >
                {selectedFields.length === ALL_EXPORT_FIELDS.length
                  ? 'Reset to Default'
                  : 'Select All'}
              </button>
            </div>

            <div className="max-h-64 overflow-y-auto space-y-2 pr-2 scrollbar-overlay">
              {ALL_EXPORT_FIELDS.map((field) => (
                <label
                  key={field.key as string}
                  className="flex items-center gap-2 py-1.5 px-2 rounded-md hover:bg-accent cursor-pointer group"
                >
                  <Checkbox
                    checked={selectedFields.includes(field.key as string)}
                    onCheckedChange={() => toggleField(field.key as string)}
                    className="h-4 w-4"
                  />
                  <span className="text-sm text-foreground group-hover:text-foreground">
                    {field.label}
                  </span>
                </label>
              ))}
            </div>

            <p className="text-xs text-muted-foreground">
              {selectedFields.length} of {ALL_EXPORT_FIELDS.length} fields selected
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 bg-muted/30 border-t flex items-center justify-between">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsOpen(false)}
            disabled={isExporting}
          >
            Cancel
          </Button>

          <Button
            onClick={handleExport}
            disabled={!canExport || selectedFields.length === 0 || isExporting}
            size="sm"
          >
            {isExporting ? (
              <>
                <div className="h-3 w-3 mr-2 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="h-3.5 w-3.5 mr-2" />
                Export {selectedFormat.toUpperCase()}
              </>
            )}
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}

export default ExportButton;
