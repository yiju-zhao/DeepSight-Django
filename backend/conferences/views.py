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
        if instance_id:
            queryset = queryset.filter(instance_id=instance_id)
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

    def _split_comma_values(self, field_value):
        """Helper to split comma-separated values and filter out blanks"""
        if not field_value:
            return []
        return [item.strip() for item in field_value.split(',') if item.strip()]

    def _split_semicolon_values(self, field_value):
        """Helper to split semicolon-separated values and filter out blanks"""
        if not field_value:
            return []
        return [item.strip() for item in field_value.split(';') if item.strip()]

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

    def _calculate_kpis(self, publications):
        """Calculate KPI metrics"""
        total_publications = publications.count()

        # Count unique authors (handle comma-separated)
        all_authors = []
        for pub in publications:
            if pub.authors:
                all_authors.extend(self._split_comma_values(pub.authors))
        unique_authors = len(set(all_authors))

        # Count unique affiliations (handle semicolon-separated values)
        all_affiliations = set()
        for pub in publications:
            if pub.aff_unique:
                affiliations = self._split_semicolon_values(pub.aff_unique)
                all_affiliations.update(affiliations)
        unique_affiliations = len(all_affiliations)

        # Count unique countries (handle comma-separated values)
        all_countries = set()
        for pub in publications:
            if pub.aff_country_unique:
                countries = self._split_comma_values(pub.aff_country_unique)
                all_countries.update(countries)
        unique_countries = len(all_countries)

        # Average rating
        avg_rating = publications.aggregate(Avg('rating'))['rating__avg'] or 0

        # Top regions (countries) - use comma-separated aff_country_unique
        region_counts = Counter()
        for pub in publications:
            if pub.aff_country_unique:
                countries = self._split_comma_values(pub.aff_country_unique)
                region_counts.update(countries)

        # Top organizations (affiliations) - use semicolon-separated aff_unique
        organization_counts = Counter()
        for pub in publications:
            if pub.aff_unique:
                affiliations = self._split_semicolon_values(pub.aff_unique)
                organization_counts.update(affiliations)

        # Resource counts
        resource_counts = {
            'with_github': publications.exclude(Q(github__isnull=True) | Q(github__exact='')).count(),
            'with_site': publications.exclude(Q(site__isnull=True) | Q(site__exact='')).count(),
            'with_pdf': publications.exclude(Q(pdf_url__isnull=True) | Q(pdf_url__exact='')).count(),
        }

        return {
            'total_publications': total_publications,
            'unique_authors': unique_authors,
            'unique_affiliations': unique_affiliations,
            'unique_countries': unique_countries,
            'avg_rating': round(avg_rating, 2),
            'session_distribution': dict(region_counts.most_common(10)),
            'author_position_distribution': dict(organization_counts.most_common(10)),
            'resource_counts': resource_counts,
        }

    def _calculate_charts(self, publications):
        """Calculate chart data"""
        # Research topics
        topics = Counter(pub.research_topic for pub in publications if pub.research_topic)

        # Top affiliations
        top_affiliations = Counter()
        for pub in publications:
            if pub.aff_unique:
                affiliations = self._split_semicolon_values(pub.aff_unique)
                top_affiliations.update(affiliations)

        # Top countries
        top_countries = Counter()
        for pub in publications:
            if pub.aff_country_unique:
                countries = self._split_comma_values(pub.aff_country_unique)
                top_countries.update(countries)

        # Top keywords
        top_keywords = Counter()
        for pub in publications:
            if pub.keywords:
                keywords = self._split_semicolon_values(pub.keywords)
                top_keywords.update(keywords)

        # Ratings histogram
        ratings = [pub.rating for pub in publications if pub.rating is not None]
        ratings_histogram = Counter([int(r) for r in ratings if r])

        # Session types
        session_types = Counter(pub.session for pub in publications if pub.session)

        # Author positions
        author_positions = Counter()
        for pub in publications:
            if pub.author_position:
                positions = self._split_comma_values(pub.author_position)
                author_positions.update(positions)

        return {
            'topics': [{'name': k, 'count': v} for k, v in topics.most_common(10)],
            'top_affiliations': [{'name': k, 'count': v} for k, v in top_affiliations.most_common(10)],
            'top_countries': [{'name': k, 'count': v} for k, v in top_countries.most_common(10)],
            'top_keywords': [{'name': k, 'count': v} for k, v in top_keywords.most_common(20)],
            'ratings_histogram': [{'rating': k, 'count': v} for k, v in sorted(ratings_histogram.items())],
            'session_types': [{'name': k, 'count': v} for k, v in session_types.items()],
            'author_positions': [{'name': k, 'count': v} for k, v in author_positions.most_common(10)],
        }

    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def list(self, request):
        """Get dashboard data for a specific instance"""
        instance_id = request.query_params.get('instance')

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

        try:
            publications = self._get_publications_queryset(instance_id=instance_id)

            # Calculate KPIs and charts
            kpis = self._calculate_kpis(publications)
            charts = self._calculate_charts(publications)

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