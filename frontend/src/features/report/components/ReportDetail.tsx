import React, { useEffect, useState } from 'react';
import { Report, ReportDetailProps, ReportContent } from '../types/type';
import { ReportService } from '../services/ReportService';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import {
  ArrowLeft,
  Download,
  Edit,
  Trash2,
  Calendar,
  Clock,
  Tag,
  Cpu,
  Search,
  FileText,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Loader2,
  HelpCircle
} from 'lucide-react';
import { Button } from "@/shared/components/ui/button";

const ReportDetail: React.FC<ReportDetailProps> = ({
  report,
  content,
  isLoading,
  onDownload,
  onDelete,
  onEdit,
  onBack
}) => {
  const [reportContent, setReportContent] = useState<ReportContent | null>(content || null);
  const [isLoadingContent, setIsLoadingContent] = useState(!content);

  useEffect(() => {
    if (!content && report.status === 'completed') {
      const loadContent = async () => {
        try {
          setIsLoadingContent(true);
          const reportService = new ReportService();
          const content = await reportService.getReportContent(report.id);
          setReportContent(content);
        } catch (error) {
          console.error('Failed to load report content:', error);
        } finally {
          setIsLoadingContent(false);
        }
      };
      loadContent();
    }
  }, [report.id, report.status, content]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'completed': return { color: 'text-emerald-600 bg-emerald-50', icon: CheckCircle2 };
      case 'failed': return { color: 'text-red-600 bg-red-50', icon: XCircle };
      case 'running': return { color: 'text-blue-600 bg-blue-50', icon: Loader2 };
      case 'pending': return { color: 'text-amber-600 bg-amber-50', icon: Clock };
      case 'cancelled': return { color: 'text-gray-600 bg-gray-50', icon: AlertCircle };
      default: return { color: 'text-gray-600 bg-gray-50', icon: HelpCircle };
    }
  };

  const statusConfig = getStatusConfig(report.status);
  const StatusIcon = statusConfig.icon;

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-[1000px] mx-auto px-6 py-8">
        {/* Back Navigation */}
        <div className="mb-6">
          <button
            onClick={onBack}
            className="flex items-center text-sm text-gray-500 hover:text-gray-900 transition-colors group"
          >
            <ArrowLeft className="w-4 h-4 mr-1 group-hover:-translate-x-1 transition-transform" />
            Back to Reports
          </button>
        </div>

        {/* Header Section */}
        <div className="mb-8 border-b border-gray-100 pb-8">
          <div className="flex flex-col gap-4">
            {/* Title */}
            <h1 className="text-4xl font-bold text-gray-900 leading-tight tracking-tight">
              {report.title || report.article_title || 'Untitled Report'}
            </h1>

            {/* Actions Row */}
            <div className="flex items-center justify-between mt-2">
              <div className="flex items-center gap-3">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusConfig.color}`}>
                  <StatusIcon className={`w-3.5 h-3.5 mr-1.5 ${report.status === 'running' ? 'animate-spin' : ''}`} />
                  {report.status.charAt(0).toUpperCase() + report.status.slice(1)}
                </span>
                <span className="text-sm text-gray-500 flex items-center">
                  <Calendar className="w-3.5 h-3.5 mr-1.5" />
                  {formatDate(report.created_at)}
                </span>
              </div>

              <div className="flex items-center gap-2">
                {report.status === 'completed' && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onDownload(report)}
                    className="h-9"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download
                  </Button>
                )}

                {onEdit && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onEdit(report)}
                    className="h-9"
                  >
                    <Edit className="h-4 w-4 mr-2" />
                    Edit
                  </Button>
                )}

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onDelete(report)}
                  className="h-9 text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200 hover:border-red-300"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Compact Metadata Grid */}
        <div className="mb-10 bg-gray-50/50 rounded-xl border border-gray-100 p-5">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-y-6 gap-x-8">
            <div className="space-y-1">
              <div className="flex items-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                <Tag className="w-3.5 h-3.5 mr-1.5" />
                Topic
              </div>
              <p className="text-sm font-medium text-gray-900 truncate" title={report.topic}>
                {report.topic || "—"}
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                <Cpu className="w-3.5 h-3.5 mr-1.5" />
                Model
              </div>
              <p className="text-sm font-medium text-gray-900 truncate">
                {report.model_provider || "—"}
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                <Search className="w-3.5 h-3.5 mr-1.5" />
                Retriever
              </div>
              <p className="text-sm font-medium text-gray-900 truncate">
                {report.retriever || "—"}
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                <FileText className="w-3.5 h-3.5 mr-1.5" />
                Sources
              </div>
              <p className="text-sm font-medium text-gray-900">
                {report.source_ids?.length || 0} files
              </p>
            </div>
          </div>

          {report.error_message && (
            <div className="mt-4 pt-4 border-t border-gray-200/60">
              <div className="flex items-start gap-2 text-red-600 bg-red-50/50 p-3 rounded-lg">
                <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                <div className="text-sm">
                  <span className="font-medium block mb-0.5">Error</span>
                  {report.error_message}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Content Section */}
        {report.status === 'completed' && (
          <div className="space-y-8">
            {isLoadingContent ? (
              <div className="space-y-6 animate-pulse max-w-3xl">
                <div className="h-4 bg-gray-100 rounded w-3/4"></div>
                <div className="space-y-3">
                  <div className="h-4 bg-gray-100 rounded"></div>
                  <div className="h-4 bg-gray-100 rounded"></div>
                  <div className="h-4 bg-gray-100 rounded w-5/6"></div>
                </div>
                <div className="h-64 bg-gray-50 rounded-xl"></div>
              </div>
            ) : reportContent ? (
              <div className="prose max-w-none prose-headings:font-bold prose-headings:tracking-tight prose-a:text-blue-600 prose-img:rounded-xl prose-pre:bg-gray-900 prose-pre:text-gray-50 prose-pre:border prose-pre:border-gray-800">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkMath]}
                  rehypePlugins={[
                    rehypeHighlight,
                    rehypeRaw,
                    [rehypeKatex, { strict: false }]
                  ]}
                  components={{
                    h1: () => null
                  }}
                >
                  {reportContent.markdown_content || reportContent.content || ''}
                </ReactMarkdown>
              </div>
            ) : (
              <div className="text-center py-12 bg-gray-50 rounded-xl border border-dashed border-gray-200">
                <p className="text-gray-500">No content available for this report.</p>
              </div>
            )}
          </div>
        )}

        {/* Processing Logs */}
        {report.processing_logs && report.processing_logs.length > 0 && (
          <div className="mt-16 pt-8 border-t border-gray-100">
            <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center">
              <Cpu className="w-4 h-4 mr-2 text-gray-400" />
              Processing Logs
            </h3>
            <div className="bg-gray-900 rounded-xl p-4 overflow-hidden">
              <div className="font-mono text-xs text-gray-300 space-y-1.5 max-h-60 overflow-y-auto custom-scrollbar">
                {report.processing_logs.map((log, index) => (
                  <div key={index} className="flex gap-3">
                    <span className="text-gray-600 shrink-0 select-none">
                      {(index + 1).toString().padStart(2, '0')}
                    </span>
                    <span>{log}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportDetail; 