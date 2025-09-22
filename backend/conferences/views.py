from django.db.models import Count, Avg, Q
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from collections import Counter

from .models import Venue, Instance, Publication, Event
from .serializers import (
    VenueSerializer, InstanceSerializer, PublicationSerializer,
    EventSerializer
)
from .utils import split_comma_values, split_semicolon_values, deduplicate_keywords, build_cooccurrence_matrix, build_fine_histogram


class StandardPageNumberPagination(PageNumberPagination):
    """Standard pagination for conferences API"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class VenueViewSet(viewsets.ModelViewSet):
    """ViewSet for Venue model"""
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    permission_classes = [IsAuthenticated]


class InstanceViewSet(viewsets.ModelViewSet):
    """ViewSet for Instance model"""
    queryset = Instance.objects.select_related('venue').all()
    serializer_class = InstanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        venue = self.request.query_params.get('venue')
        if venue:
            queryset = queryset.filter(venue__name__iexact=venue)
        return queryset


class PublicationViewSet(viewsets.ModelViewSet):
    """ViewSet for Publication model"""
    queryset = Publication.objects.select_related('instance__venue').all()
    serializer_class = PublicationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPageNumberPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        instance_id = self.request.query_params.get('instance')
        search = self.request.query_params.get('search')
        ordering = self.request.query_params.get('ordering')

        if instance_id:
            queryset = queryset.filter(instance_id=instance_id)

        if search:
            # Search in title, authors, and keywords (case-insensitive)
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(authors__icontains=search) |
                Q(keywords__icontains=search)
            )

        # Apply ordering
        if ordering:
            # Support for title and rating ordering
            if ordering in ['title', '-title', 'rating', '-rating']:
                queryset = queryset.order_by(ordering)
            else:
                # Default ordering by rating descending
                queryset = queryset.order_by('-rating')
        else:
            # Default ordering by rating descending
            queryset = queryset.order_by('-rating')

        return queryset


class EventViewSet(viewsets.ModelViewSet):
    """ViewSet for Event model"""
    queryset = Event.objects.select_related('instance__venue').all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPageNumberPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        instance_id = self.request.query_params.get('instance')
        if instance_id:
            queryset = queryset.filter(instance_id=instance_id)
        return queryset


class OverviewViewSet(viewsets.ViewSet):
    """ViewSet for dashboard analytics and overview"""
    permission_classes = [IsAuthenticated]


    def _get_publications_queryset(self, venue=None, year=None, instance_id=None):
        """Get filtered publications queryset"""
        queryset = Publication.objects.select_related('instance__venue')

        if instance_id:
            queryset = queryset.filter(instance_id=instance_id)
        elif venue and year:
            queryset = queryset.filter(
                instance__venue__name__iexact=venue,
                instance__year=year
            )
        else:
            raise Http404("Either instance ID or both venue and year must be provided")

        return queryset

    def _process_dashboard_data(self, publications):
        """Process publications data once for all dashboard views"""

        # Get the raw publication data once
        pub_list = list(publications)  # Execute query once
        total_publications = len(pub_list)

        # Process all data in one pass
        all_authors = []
        all_countries = []
        all_affiliations = []
        all_keywords = []
        all_topics = []
        all_sessions = []
        all_ratings = []
        all_author_positions = []

        # New data structures for visualizations
        countries_per_publication = []
        affiliations_per_publication = []
        organization_research_areas = []

        resource_counts = {'with_github': 0, 'with_site': 0, 'with_pdf': 0}

        for pub in pub_list:
            # Authors (semicolon-separated - as stored in DB)
            if pub.authors:
                authors = split_semicolon_values(pub.authors)
                all_authors.extend(authors)

            # Countries (semicolon-separated - as stored in DB)
            if pub.aff_country_unique:
                countries = split_semicolon_values(pub.aff_country_unique)
                all_countries.extend(countries)
                # Store unique countries per publication for collaboration analysis
                countries_per_publication.append(list(set(countries)))
            else:
                countries_per_publication.append([])

            # Affiliations (semicolon-separated)
            if pub.aff_unique:
                affiliations = split_semicolon_values(pub.aff_unique)
                all_affiliations.extend(affiliations)
                # Store unique affiliations per publication for collaboration analysis
                affiliations_per_publication.append(list(set(affiliations)))

                # Store organization and research area pairs for stacked chart
                research_area = pub.research_topic if pub.research_topic else None
                # Only add one entry per publication (not per affiliation) to count publications correctly
                organization_research_areas.append({
                    'publication_id': pub.id,
                    'affiliations': list(set(affiliations)),
                    'research_area': research_area
                })
            else:
                affiliations_per_publication.append([])

            # Keywords (semicolon-separated)
            if pub.keywords:
                keywords = split_semicolon_values(pub.keywords)
                all_keywords.extend(keywords)

            # Topics
            if pub.research_topic:
                all_topics.append(pub.research_topic)

            # Sessions
            if pub.session:
                all_sessions.append(pub.session)

            # Ratings
            if pub.rating is not None:
                all_ratings.append(pub.rating)

            # Author positions (semicolon-separated - as stored in DB)
            if pub.author_position:
                positions = split_semicolon_values(pub.author_position)
                all_author_positions.extend(positions)

            # Resource counts
            if pub.github and pub.github.strip():
                resource_counts['with_github'] += 1
            if pub.site and pub.site.strip():
                resource_counts['with_site'] += 1
            if pub.pdf_url and pub.pdf_url.strip():
                resource_counts['with_pdf'] += 1

        # Calculate counters once
        topics_counter = Counter(all_topics)
        affiliations_counter = Counter(all_affiliations)
        countries_counter = Counter(all_countries)

        # Deduplicate keywords (e.g., "LLM", "llm", "LLMs" -> "LLM")
        keywords_deduplicated = deduplicate_keywords(all_keywords)

        sessions_counter = Counter(all_sessions)
        ratings_counter = Counter([int(r) for r in all_ratings if r])
        author_positions_counter = Counter(all_author_positions)

        # Calculate average rating
        avg_rating = sum(all_ratings) / len(all_ratings) if all_ratings else 0

        # Return all processed data
        return {
            'total_publications': total_publications,
            'unique_authors': len(set(all_authors)),
            'unique_affiliations': len(set(all_affiliations)),
            'unique_countries': len(set(all_countries)),
            'avg_rating': round(avg_rating, 2),
            'resource_counts': resource_counts,
            'counters': {
                'topics': topics_counter,
                'affiliations': affiliations_counter,
                'countries': countries_counter,
                'keywords': keywords_deduplicated,
                'sessions': sessions_counter,
                'ratings': ratings_counter,
                'author_positions': author_positions_counter,
            },
            'raw_data': {
                'countries_per_publication': countries_per_publication,
                'affiliations_per_publication': affiliations_per_publication,
                'all_ratings': all_ratings,  # Keep original float ratings for fine histogram
                'organization_research_areas': organization_research_areas,
            }
        }

    def _build_organization_publications(self, raw_data):
        """Build organization publications data grouped by research area using same logic as org collaboration chart"""
        organization_research_areas = raw_data.get('organization_research_areas', [])

        # Use same counting logic as build_cooccurrence_matrix
        org_area_totals = Counter()  # (org, area) -> count
        org_totals = Counter()       # org -> total count

        for item in organization_research_areas:
            affiliations = item['affiliations']
            area = item['research_area'] or 'Publications'

            # Convert to set to ensure uniqueness within publication (same as cooccurrence matrix)
            unique_affiliations = set(affiliations)

            # Count each organization's participation in this publication (same logic as line 166 in utils.py)
            for org in unique_affiliations:
                org_totals[org] += 1
                org_area_totals[(org, area)] += 1

        # Convert to the expected format
        result = []
        for org, total in org_totals.items():
            research_area_counts = {}

            # Get counts for each research area for this org
            for (counted_org, area), count in org_area_totals.items():
                if counted_org == org:
                    research_area_counts[area] = count

            result.append({
                'organization': org,
                'total': total,
                'research_areas': research_area_counts
            })

        # Sort by total publications descending and take top 15
        result.sort(key=lambda x: x['total'], reverse=True)
        return result[:15]

    def _build_kpis(self, processed_data):
        """Build KPI data from processed data"""
        return {
            'total_publications': processed_data['total_publications'],
            'unique_authors': processed_data['unique_authors'],
            'unique_affiliations': processed_data['unique_affiliations'],
            'unique_countries': processed_data['unique_countries'],
            'avg_rating': processed_data['avg_rating'],
            'session_distribution': dict(processed_data['counters']['countries'].most_common(10)),
            'author_position_distribution': dict(processed_data['counters']['affiliations'].most_common(10)),
            'resource_counts': processed_data['resource_counts'],
        }

    def _build_charts(self, processed_data, bin_size=0.5):
        """Build chart data from processed data"""
        counters = processed_data['counters']
        raw_data = processed_data.get('raw_data', {})

        # Build collaboration chord diagrams
        country_chord = build_cooccurrence_matrix(
            raw_data.get('countries_per_publication', []),
            top_n=8
        )

        org_chord = build_cooccurrence_matrix(
            raw_data.get('affiliations_per_publication', []),
            top_n=10
        )

        # Build fine-grained histogram
        ratings_histogram_fine = build_fine_histogram(
            raw_data.get('all_ratings', []),
            bin_size=bin_size
        )

        # Build keywords treemap data
        keywords_treemap = [
            {'name': k, 'value': v}
            for k, v in sorted(counters['keywords'].items(), key=lambda x: x[1], reverse=True)[:30]
        ]

        # Build organization publications data (stacked by research area)
        organization_publications = self._build_organization_publications(raw_data)

        return {
            'topics': [{'name': k, 'count': v} for k, v in counters['topics'].most_common(10)],
            'top_affiliations': [{'name': k, 'count': v} for k, v in counters['affiliations'].most_common(10)],
            'top_countries': [{'name': k, 'count': v} for k, v in counters['countries'].most_common(10)],
            'top_keywords': [{'name': k, 'count': v} for k, v in sorted(counters['keywords'].items(), key=lambda x: x[1], reverse=True)[:20]],
            'ratings_histogram': [{'rating': k, 'count': v} for k, v in sorted(counters['ratings'].items())],
            'session_types': [{'name': k, 'count': v} for k, v in counters['sessions'].items()],
            'author_positions': [{'name': k, 'count': v} for k, v in counters['author_positions'].most_common(10)],
            # New visualizations
            'chords': {
                'country': country_chord,
                'org': org_chord
            },
            'ratings_histogram_fine': ratings_histogram_fine,
            'keywords_treemap': keywords_treemap,
            'organization_publications': organization_publications,
        }

    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def list(self, request):
        """Get dashboard data for a specific instance"""
        instance_id = request.query_params.get('instance')
        bin_size_param = request.query_params.get('bin_size', '0.5')

        if not instance_id:
            return Response(
                {'error': 'instance parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            instance_id = int(instance_id)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid instance parameter'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse and validate bin_size parameter
        try:
            bin_size = float(bin_size_param)
            # Clamp to reasonable bounds
            bin_size = max(0.1, min(2.0, bin_size))
        except (ValueError, TypeError):
            bin_size = 0.5  # Default fallback

        try:
            publications = self._get_publications_queryset(instance_id=instance_id)

            # Process data once for all views
            processed_data = self._process_dashboard_data(publications)

            # Build KPIs and charts from processed data
            kpis = self._build_kpis(processed_data)
            charts = self._build_charts(processed_data, bin_size=bin_size)

            response_data = {
                'kpis': kpis,
                'charts': charts,
            }

            return Response(response_data)

        except Http404 as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @method_decorator(cache_page(60 * 30))  # Cache for 30 minutes
    @action(detail=False, methods=['get'])
    def general(self, request):
        """Get general conferences overview statistics"""
        venues = Venue.objects.all()
        instances = Instance.objects.select_related('venue').all()
        publications = Publication.objects.all()

        total_conferences = venues.count()
        total_papers = publications.count()
        years_covered = sorted(set(instances.values_list('year', flat=True)))
        avg_papers_per_year = total_papers / len(years_covered) if years_covered else 0

        # Conference summary
        conferences = []
        for venue in venues:
            venue_instances = instances.filter(venue=venue)
            venue_papers = publications.filter(instance__venue=venue).count()
            conferences.append({
                'name': venue.name,
                'type': venue.type,
                'instances': venue_instances.count(),
                'total_papers': venue_papers,
                'years': sorted(venue_instances.values_list('year', flat=True))
            })

        response_data = {
            'total_conferences': total_conferences,
            'total_papers': total_papers,
            'years_covered': years_covered,
            'avg_papers_per_year': round(avg_papers_per_year, 1),
            'conferences': conferences,
        }

        return Response(response_data)