/**
 * Publication Detail Modal Component
 *
 * Displays comprehensive information about a publication:
 * - Full metadata (title, authors, abstract, affiliations)
 * - Resource links (PDF, GitHub, website, DOI)
 * - Keywords and research topics
 * - Quick actions (favorite, export, share)
 * - Related publications (optional)
 */

import { useState, useMemo } from 'react';
import {
  X,
  ExternalLink,
  Github,
  FileText,
  Star,
  StarOff,
  Download,
  Share2,
  Copy,
  Check,
  Building2,
  Globe,
  Tag,
  Calendar,
  Award,
  Users,
} from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/shared/components/ui/dialog';
import { Badge } from '@/shared/components/ui/badge';
import { Separator } from '@/shared/components/ui/separator';
import { Card, CardContent } from '@/shared/components/ui/card';
import { PublicationTableItem } from '../types';
import { useFavorites } from '../hooks/useFavorites';
import { exportToCSV } from '../utils/export';
import { splitSemicolonValues } from '@/shared/utils/utils';

interface PublicationDetailModalProps {
  publication: PublicationTableItem | null;
  isOpen: boolean;
  onClose: () => void;
}

// ============================================================================
// RESOURCE LINK BUTTON
// ============================================================================

interface ResourceLinkProps {
  href?: string;
  icon: React.ElementType;
  label: string;
  variant?: 'default' | 'pdf' | 'github' | 'site';
}

const ResourceLink = ({ href, icon: Icon, label, variant = 'default' }: ResourceLinkProps) => {
  if (!href) return null;

  const colorClasses = {
    default: 'text-gray-700 hover:text-gray-900 hover:bg-gray-100',
    pdf: 'text-red-600 hover:text-red-700 hover:bg-red-50',
    github: 'text-gray-700 hover:text-gray-900 hover:bg-gray-100',
    site: 'text-blue-600 hover:text-blue-700 hover:bg-blue-50',
  };

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={`flex items-center gap-2 px-4 py-2 rounded-md border transition-all ${colorClasses[variant]}`}
    >
      <Icon className="h-4 w-4" />
      <span className="text-sm font-medium">{label}</span>
      <ExternalLink className="h-3 w-3 ml-auto" />
    </a>
  );
};

// ============================================================================
// METADATA SECTION
// ============================================================================

interface MetadataSectionProps {
  icon: React.ElementType;
  label: string;
  children: React.ReactNode;
}

const MetadataSection = ({ icon: Icon, label, children }: MetadataSectionProps) => {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
        <Icon className="h-4 w-4 text-muted-foreground" />
        {label}
      </div>
      <div className="pl-6">{children}</div>
    </div>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function PublicationDetailModal({
  publication,
  isOpen,
  onClose,
}: PublicationDetailModalProps) {
  const [copied, setCopied] = useState(false);
  const { isFavorite, toggleFavorite } = useFavorites();

  // Parse arrays from semicolon-separated strings
  const authors = useMemo(() => {
    return publication ? splitSemicolonValues(publication.authors) : [];
  }, [publication]);

  const keywords = useMemo(() => {
    return publication ? splitSemicolonValues(publication.keywords) : [];
  }, [publication]);

  const countries = useMemo(() => {
    return publication?.aff_country_unique
      ? splitSemicolonValues(publication.aff_country_unique)
      : [];
  }, [publication]);

  const organizations = useMemo(() => {
    return publication?.aff_unique
      ? splitSemicolonValues(publication.aff_unique)
      : [];
  }, [publication]);

  // Check if favorited
  const favorited = publication ? isFavorite(String(publication.id)) : false;

  // Handle copy citation
  const handleCopyTitle = async () => {
    if (!publication) return;

    const citation = `${publication.title} - ${publication.venue_name} ${publication.instance_year}`;
    await navigator.clipboard.writeText(citation);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Handle export single publication
  const handleExport = () => {
    if (!publication) return;

    exportToCSV(
      [publication],
      undefined,
      `publication-${publication.id}.csv`
    );
  };

  // Handle favorite toggle
  const handleToggleFavorite = () => {
    if (!publication) return;
    toggleFavorite(String(publication.id));
  };

  if (!publication) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 space-y-2">
              <DialogTitle className="text-2xl font-bold leading-tight pr-8">
                {publication.title}
              </DialogTitle>

              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant="outline" className="gap-1">
                  <Calendar className="h-3 w-3" />
                  {publication.venue_name} {publication.instance_year}
                </Badge>

                {publication.rating && (
                  <Badge variant="secondary" className="gap-1">
                    <Star className="h-3 w-3 text-amber-500 fill-current" />
                    {publication.rating.toFixed(1)}
                  </Badge>
                )}

                {publication.session && (
                  <Badge variant="outline">{publication.session}</Badge>
                )}
              </div>
            </div>

            <button
              onClick={onClose}
              className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
            >
              <X className="h-5 w-5" />
              <span className="sr-only">Close</span>
            </button>
          </div>
        </DialogHeader>

        <div className="space-y-6 mt-6">
          {/* Quick Actions */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleToggleFavorite}
              className="gap-2"
            >
              {favorited ? (
                <>
                  <Star className="h-4 w-4 text-amber-500 fill-current" />
                  Favorited
                </>
              ) : (
                <>
                  <StarOff className="h-4 w-4" />
                  Add to Favorites
                </>
              )}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={handleCopyTitle}
              className="gap-2"
            >
              {copied ? (
                <>
                  <Check className="h-4 w-4 text-green-600" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4" />
                  Copy Citation
                </>
              )}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={handleExport}
              className="gap-2"
            >
              <Download className="h-4 w-4" />
              Export
            </Button>
          </div>

          <Separator />

          {/* Resource Links */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            <ResourceLink
              href={publication.pdf_url}
              icon={FileText}
              label="View PDF"
              variant="pdf"
            />
            <ResourceLink
              href={publication.github}
              icon={Github}
              label="View Code"
              variant="github"
            />
            <ResourceLink
              href={publication.site}
              icon={ExternalLink}
              label="Project Site"
              variant="site"
            />
          </div>

          <Separator />

          {/* Metadata Sections */}
          <div className="space-y-6">
            {/* Authors */}
            {authors.length > 0 && (
              <MetadataSection icon={Users} label="Authors">
                <div className="flex flex-wrap gap-2">
                  {authors.map((author, index) => (
                    <Badge key={index} variant="secondary">
                      {author}
                    </Badge>
                  ))}
                </div>
              </MetadataSection>
            )}

            {/* Organizations */}
            {organizations.length > 0 && (
              <MetadataSection icon={Building2} label="Organizations">
                <div className="flex flex-wrap gap-2">
                  {organizations.slice(0, 10).map((org, index) => (
                    <Badge key={index} variant="outline">
                      {org}
                    </Badge>
                  ))}
                  {organizations.length > 10 && (
                    <Badge variant="outline">+{organizations.length - 10} more</Badge>
                  )}
                </div>
              </MetadataSection>
            )}

            {/* Countries */}
            {countries.length > 0 && (
              <MetadataSection icon={Globe} label="Countries">
                <div className="flex flex-wrap gap-2">
                  {countries.map((country, index) => (
                    <Badge key={index} variant="outline" className="gap-1">
                      <Globe className="h-3 w-3" />
                      {country}
                    </Badge>
                  ))}
                </div>
              </MetadataSection>
            )}

            {/* Research Topic */}
            {publication.research_topic && (
              <MetadataSection icon={Award} label="Research Topic">
                <Badge variant="default">{publication.research_topic}</Badge>
              </MetadataSection>
            )}

            {/* Keywords */}
            {keywords.length > 0 && (
              <MetadataSection icon={Tag} label="Keywords">
                <div className="flex flex-wrap gap-2">
                  {keywords.map((keyword, index) => (
                    <Badge key={index} variant="secondary" className="gap-1">
                      <Tag className="h-3 w-3" />
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </MetadataSection>
            )}
          </div>

          {/* Related Publications Placeholder */}
          <Card className="bg-muted/30">
            <CardContent className="p-4">
              <div className="text-sm text-muted-foreground text-center">
                <p className="font-medium mb-1">Related Publications</p>
                <p className="text-xs">
                  Feature coming soon - we'll show publications with similar topics and keywords
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default PublicationDetailModal;
