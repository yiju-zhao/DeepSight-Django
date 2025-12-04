from collections import Counter

from django.db.models import Q
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.core.exceptions import ValidationError

from .models import Event, Instance, Publication, Session, Venue
from .serializers import (
    ActiveImportSerializer,
    EventSerializer,
    ImportResponseSerializer,
    ImportToNotebookRequestSerializer,
    InstanceSerializer,
    PublicationSerializer,
    PublicationTableSerializer,
    SessionSerializer,
    VenueSerializer,
)
from .services import conference_import_service
from .utils import (
    build_fine_histogram,
    deduplicate_keywords,
    split_semicolon_values,
)


class StandardPageNumberPagination(PageNumberPagination):
    """Standard pagination for conferences API"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 1000  # Increased to allow bulk retrieval for semantic search


class VenueViewSet(viewsets.ModelViewSet):
    """ViewSet for Venue model"""

    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    permission_classes = [IsAuthenticated]


class InstanceViewSet(viewsets.ModelViewSet):
    """ViewSet for Instance model"""

    queryset = Instance.objects.select_related("venue").all()
    serializer_class = InstanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        venue = self.request.query_params.get("venue")
        if venue:
            queryset = queryset.filter(venue__name__iexact=venue)
        return queryset


class PublicationViewSet(viewsets.ModelViewSet):
    """ViewSet for Publication model"""

    queryset = Publication.objects.select_related("instance__venue").all()
    serializer_class = PublicationTableSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPageNumberPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        instance_id = self.request.query_params.get("instance")
        search = self.request.query_params.get("search")
        aff_filter = self.request.query_params.get("aff_filter")
        ordering = self.request.query_params.get("ordering")

        if instance_id:
            queryset = queryset.filter(instance_id=instance_id)

        if search:
            # Search in title, authors, and keywords (case-insensitive)
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(authors__icontains=search)
                | Q(keywords__icontains=search)
            )

        if aff_filter:
            # Filter by affiliation (supports multiple affiliations with OR logic)
            affiliations = [aff.strip() for aff in aff_filter.split(",") if aff.strip()]
            if affiliations:
                # Build Q objects for each affiliation and combine with OR
                aff_queries = Q()
                for affiliation in affiliations:
                    aff_queries |= Q(aff_unique__icontains=affiliation)
                queryset = queryset.filter(aff_queries)

        # Filter out publications with status "reject"
        queryset = queryset.exclude(session__iexact="reject")

        # Apply ordering
        if ordering:
            # Support for title and rating ordering
            if ordering in ["title", "-title", "rating", "-rating"]:
                queryset = queryset.order_by(ordering)
            else:
                # Default ordering by rating descending
                queryset = queryset.order_by("-rating")
        else:
            # Default ordering by rating descending
            queryset = queryset.order_by("-rating")

        return queryset

    @action(detail=False, methods=["post"], url_path="import-to-notebook")
    def import_to_notebook(self, request):
        """
        Import selected publications to a notebook.

        Request body:
        {
            "publication_ids": ["uuid1", "uuid2", ...],
            "action": "add" | "create",
            "notebook_id": "uuid" (required if action="add"),
            "notebook_name": "name" (required if action="create")
        }
        """
        # Validate request data
        serializer = ImportToNotebookRequestSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        publication_ids = validated_data["publication_ids"]
        action = validated_data["action"]

        # Get or create notebook
        from notebooks.models import Notebook

        if action == "add":
            # Get existing notebook
            notebook_id = validated_data["notebook_id"]
            try:
                notebook = Notebook.objects.get(id=notebook_id, user=request.user)
            except Notebook.DoesNotExist:
                return Response(
                    {"error": f"Notebook {notebook_id} not found or not accessible"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:  # action == "create"
            # Create new notebook using service layer to ensure RAGFlow dataset is created
            notebook_name = validated_data["notebook_name"]
            from notebooks.services import NotebookService

            notebook_service = NotebookService()
            try:
                notebook = notebook_service.create_notebook(
                    user=request.user,
                    name=notebook_name,
                    description="",
                )
            except ValidationError as e:
                return Response(
                    {"error": f"Failed to create notebook: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Import publications using service
        result = conference_import_service.import_publications_to_notebook(
            publication_ids=publication_ids,
            notebook=notebook,
            user=request.user,
        )

        # Add notebook info to response
        result["notebook_id"] = str(notebook.id)
        result["notebook_name"] = notebook.name

        # Return response with appropriate status code
        response_serializer = ImportResponseSerializer(result)
        return Response(response_serializer.data, status=result["status_code"])

    @action(detail=False, methods=["get"], url_path="import-status")
    def import_status(self, request):
        """
        Get active and recent conference import jobs for the current user.

        Returns list of import jobs with progress information.
        """
        active_imports = conference_import_service.get_active_imports(request.user)

        serializer = ActiveImportSerializer(active_imports, many=True)
        return Response(serializer.data)


class EventViewSet(viewsets.ModelViewSet):
    """ViewSet for Event model"""

    queryset = Event.objects.select_related("instance__venue").all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPageNumberPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        instance_id = self.request.query_params.get("instance")
        if instance_id:
            queryset = queryset.filter(instance_id=instance_id)
        return queryset



class SessionViewSet(viewsets.ModelViewSet):
    """ViewSet for Session model"""

    queryset = Session.objects.select_related("instance__venue").all()
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPageNumberPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        instance_id = self.request.query_params.get("instance")
        if instance_id:
            queryset = queryset.filter(instance_id=instance_id)
        return queryset


class OverviewViewSet(viewsets.ViewSet):
    """ViewSet for dashboard analytics and overview"""

    permission_classes = [IsAuthenticated]

    def _get_publications_queryset(self, venue=None, year=None, instance_id=None):
        """Get filtered publications queryset"""
        queryset = Publication.objects.select_related("instance__venue")

        if instance_id:
            queryset = queryset.filter(instance_id=instance_id)
        elif venue and year:
            queryset = queryset.filter(
                instance__venue__name__iexact=venue, instance__year=year
            )
        else:
            raise Http404("Either instance ID or both venue and year must be provided")

        # Filter out publications with status "reject"
        queryset = queryset.exclude(session__iexact="reject")

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
        publications_with_affiliations_and_topics = []  # Store full publication data

        resource_counts = {"with_github": 0, "with_site": 0, "with_pdf": 0}

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

                # Store publication with affiliations and research topic for stacked chart
                publications_with_affiliations_and_topics.append(
                    {
                        "affiliations": list(set(affiliations)),
                        "research_topic": pub.research_topic,
                    }
                )
            else:
                affiliations_per_publication.append([])
                publications_with_affiliations_and_topics.append(
                    {"affiliations": [], "research_topic": pub.research_topic}
                )

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
                resource_counts["with_github"] += 1
            if pub.site and pub.site.strip():
                resource_counts["with_site"] += 1
            if pub.pdf_url and pub.pdf_url.strip():
                resource_counts["with_pdf"] += 1

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
            "total_publications": total_publications,
            "unique_authors": len(set(all_authors)),
            "unique_affiliations": len(set(all_affiliations)),
            "unique_countries": len(set(all_countries)),
            "avg_rating": round(avg_rating, 2),
            "resource_counts": resource_counts,
            "counters": {
                "topics": topics_counter,
                "affiliations": affiliations_counter,
                "countries": countries_counter,
                "keywords": keywords_deduplicated,
                "sessions": sessions_counter,
                "ratings": ratings_counter,
                "author_positions": author_positions_counter,
            },
            "raw_data": {
                "countries_per_publication": countries_per_publication,
                "affiliations_per_publication": affiliations_per_publication,
                "publications_with_affiliations_and_topics": publications_with_affiliations_and_topics,
                "all_ratings": all_ratings,  # Keep original float ratings for fine histogram
            },
        }

    def _build_organization_publications(self, raw_data):
        """Build organization publications data with simple counting: if pub has (A,B) then A+1, B+1"""
        affiliations_per_publication = raw_data.get("affiliations_per_publication", [])

        # Simple counting: each organization gets +1 for each publication it appears in
        org_totals = Counter()

        for affiliations in affiliations_per_publication:
            # Remove empty strings and strip whitespace
            clean_affiliations = [aff.strip() for aff in affiliations if aff.strip()]

            # Each organization in this publication gets +1
            for org in clean_affiliations:
                org_totals[org] += 1

        # Convert to the expected format
        result = []
        for org, total in org_totals.items():
            result.append(
                {
                    "organization": org,
                    "total": total,
                    "research_areas": {},  # Empty since we're not breaking down by research area anymore
                }
            )

        # Sort by total publications descending and take top 15
        result.sort(key=lambda x: x["total"], reverse=True)
        return result[:15]

    def _build_organization_publications_by_research_area(self, raw_data):
        """Build organization publications data grouped by research areas (stacked bar chart format)"""
        publications_data = raw_data.get(
            "publications_with_affiliations_and_topics", []
        )

        # Count publications by organization and research area
        org_research_counts = {}

        for pub_data in publications_data:
            affiliations = pub_data.get("affiliations", [])
            research_topic = pub_data.get("research_topic", "")

            # Extract research area (part before ->)
            research_area = (
                research_topic.split("->")[0].strip()
                if research_topic and "->" in research_topic
                else research_topic
            )

            # Skip unknown/empty research areas - they'll be counted in Others later
            if not research_area or research_area.lower() in ["unknown", "none", ""]:
                research_area = None

            # Count for each organization
            for org in affiliations:
                org = org.strip()
                if not org:
                    continue

                if org not in org_research_counts:
                    org_research_counts[org] = {}

                # Only count valid research areas
                if research_area:
                    if research_area not in org_research_counts[org]:
                        org_research_counts[org][research_area] = 0
                    org_research_counts[org][research_area] += 1

        # Calculate total publications per organization (including unknown/none)
        # We need the actual total from the original data, not just the known research areas
        org_total_pubs = {}
        for pub_data in publications_data:
            affiliations = pub_data.get("affiliations", [])
            for org in affiliations:
                org = org.strip()
                if not org:
                    continue
                if org not in org_total_pubs:
                    org_total_pubs[org] = 0
                org_total_pubs[org] += 1

        # Get top 15 organizations by total publications
        top_orgs = sorted(org_total_pubs.items(), key=lambda x: x[1], reverse=True)[:15]
        top_org_names = [org for org, _ in top_orgs]

        # Get all research areas from top organizations
        all_research_areas = set()
        for org in top_org_names:
            if org in org_research_counts:
                all_research_areas.update(org_research_counts[org].keys())

        # Count total publications per research area to find top 9
        research_area_totals = {}
        for research_area in all_research_areas:
            total = 0
            for org in top_org_names:
                if (
                    org in org_research_counts
                    and research_area in org_research_counts[org]
                ):
                    total += org_research_counts[org][research_area]
            research_area_totals[research_area] = total

        # Get top 9 research areas
        top_research_areas = sorted(
            research_area_totals.items(), key=lambda x: x[1], reverse=True
        )[:9]
        top_research_area_names = [area for area, _ in top_research_areas]

        # Build result in the requested format
        result = []
        for org in top_org_names:
            org_data = {"organization": org}

            # Add top 9 research areas
            top_9_total = 0
            for research_area in top_research_area_names:
                count = org_research_counts.get(org, {}).get(research_area, 0)
                org_data[research_area] = count
                top_9_total += count

            # Calculate "Others" as: total_publications - top_9_total
            # This includes unknown/none areas + remaining research areas
            total_pubs = org_total_pubs.get(org, 0)
            others_count = total_pubs - top_9_total

            if others_count > 0:
                org_data["Others"] = others_count

            result.append(org_data)

        return result

    def _convert_to_force_graph(self, chord_data):
        """Convert chord diagram data to force graph format (nodes and links)"""
        if not chord_data or not chord_data.get("keys") or not chord_data.get("matrix"):
            return {"nodes": [], "links": []}

        keys = chord_data["keys"]
        matrix = chord_data["matrix"]
        totals = chord_data.get("totals", {})

        # Create nodes
        nodes = []
        for i, key in enumerate(keys):
            nodes.append(
                {
                    "id": key,
                    "val": totals.get(key, 1),  # Node size based on total publications
                    "group": 1,  # All same group for now
                }
            )

        # Create links from matrix (only for collaborations, skip diagonal)
        links = []
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):  # Only upper triangle (avoid duplicates)
                weight = matrix[i][j]
                if weight > 0:  # Only create links if there are collaborations
                    links.append(
                        {
                            "source": keys[i],
                            "target": keys[j],
                            "value": weight,  # Link thickness based on collaboration count
                        }
                    )

        return {"nodes": nodes, "links": links}

    def _build_country_force_graph(self, raw_data):
        """Build force graph data for countries directly from publication data"""
        countries_per_publication = raw_data.get("countries_per_publication", [])

        # Count total publications per country
        country_totals = Counter()
        # Count collaborations between countries
        country_collaborations = Counter()

        for countries in countries_per_publication:
            # Remove empty strings and strip whitespace
            clean_countries = [
                country.strip() for country in countries if country.strip()
            ]

            # Count total publications per country
            for country in clean_countries:
                country_totals[country] += 1

            # Count collaborations (pairs of countries in same publication)
            if len(clean_countries) > 1:
                for i, country1 in enumerate(clean_countries):
                    for j, country2 in enumerate(clean_countries):
                        if i < j:  # Avoid duplicates
                            # Use sorted tuple for consistent ordering
                            pair = tuple(sorted([country1, country2]))
                            country_collaborations[pair] += 1

        # Get all countries (not limited to top 8)
        all_countries = list(country_totals.keys())

        # Create nodes for all countries
        nodes = []
        for country in all_countries:
            nodes.append(
                {
                    "id": country,
                    "val": country_totals[
                        country
                    ],  # Node size based on total publications
                    "group": 1,
                }
            )

        # Create links between all countries
        links = []
        for (country1, country2), collab_count in country_collaborations.items():
            if country1 in all_countries and country2 in all_countries:
                links.append(
                    {
                        "source": country1,
                        "target": country2,
                        "value": collab_count,  # Particle speed based on collaboration count
                    }
                )

        return {"nodes": nodes, "links": links}

    def _build_organization_force_graph(self, raw_data):
        """Build force graph data for organizations directly from publication data"""
        affiliations_per_publication = raw_data.get("affiliations_per_publication", [])

        # Count total publications per organization
        org_totals = Counter()
        # Count collaborations between organizations
        org_collaborations = Counter()

        for affiliations in affiliations_per_publication:
            # Remove empty strings and strip whitespace
            clean_affiliations = [aff.strip() for aff in affiliations if aff.strip()]

            # Count total publications per organization
            for org in clean_affiliations:
                org_totals[org] += 1

            # Count collaborations (pairs of organizations in same publication)
            if len(clean_affiliations) > 1:
                for i, org1 in enumerate(clean_affiliations):
                    for j, org2 in enumerate(clean_affiliations):
                        if i < j:  # Avoid duplicates
                            # Use sorted tuple for consistent ordering
                            pair = tuple(sorted([org1, org2]))
                            org_collaborations[pair] += 1

        # Get top 15 organizations by publication count for cleaner visualization
        top_orgs = [org for org, count in org_totals.most_common(15)]

        # Create nodes for top 15 organizations
        nodes = []
        for org in top_orgs:
            nodes.append(
                {
                    "id": org,
                    "val": org_totals[org],  # Node size based on total publications
                    "group": 1,
                }
            )

        # Create links between top 15 organizations only
        links = []
        for (org1, org2), collab_count in org_collaborations.items():
            if org1 in top_orgs and org2 in top_orgs:
                links.append(
                    {
                        "source": org1,
                        "target": org2,
                        "value": collab_count,  # Particle speed based on collaboration count
                    }
                )

        return {"nodes": nodes, "links": links}

    def _build_kpis(self, processed_data):
        """Build KPI data from processed data"""
        return {
            "total_publications": processed_data["total_publications"],
            "unique_authors": processed_data["unique_authors"],
            "unique_affiliations": processed_data["unique_affiliations"],
            "unique_countries": processed_data["unique_countries"],
            "avg_rating": processed_data["avg_rating"],
            "session_distribution": dict(
                processed_data["counters"]["countries"].most_common(10)
            ),
            "author_position_distribution": dict(
                processed_data["counters"]["affiliations"].most_common(10)
            ),
            "resource_counts": processed_data["resource_counts"],
        }

    def _build_charts(self, processed_data, bin_size=0.5):
        """Build chart data from processed data"""
        counters = processed_data["counters"]
        raw_data = processed_data.get("raw_data", {})

        # Build force graph data for countries directly from raw data
        country_force_graph = self._build_country_force_graph(raw_data)

        # Build force graph data for organizations directly from raw data
        organization_force_graph = self._build_organization_force_graph(raw_data)

        # Build fine-grained histogram
        ratings_histogram_fine = build_fine_histogram(
            raw_data.get("all_ratings", []), bin_size=bin_size
        )

        # Build keywords treemap data
        keywords_treemap = [
            {"name": k, "value": v}
            for k, v in sorted(
                counters["keywords"].items(), key=lambda x: x[1], reverse=True
            )[:30]
        ]

        # Build organization publications data using exact same logic as collaboration chart
        organization_publications = self._build_organization_publications(raw_data)

        # Build organization publications data grouped by research areas
        organization_publications_by_research_area = (
            self._build_organization_publications_by_research_area(raw_data)
        )

        return {
            "topics": [
                {"name": k, "count": v} for k, v in counters["topics"].most_common(10)
            ],
            "top_affiliations": [
                {"name": k, "count": v}
                for k, v in counters["affiliations"].most_common(10)
            ],
            "top_countries": [
                {"name": k, "count": v}
                for k, v in counters["countries"].most_common(10)
            ],
            "top_keywords": [
                {"name": k, "count": v}
                for k, v in sorted(
                    counters["keywords"].items(), key=lambda x: x[1], reverse=True
                )[:20]
            ],
            "ratings_histogram": [
                {"rating": k, "count": v}
                for k, v in sorted(counters["ratings"].items())
            ],
            "session_types": [
                {"name": k, "count": v} for k, v in counters["sessions"].items()
            ],
            "author_positions": [
                {"name": k, "count": v}
                for k, v in counters["author_positions"].most_common(10)
            ],
            # New visualizations
            "force_graphs": {
                "country": country_force_graph,
                "organization": organization_force_graph,
            },
            "ratings_histogram_fine": ratings_histogram_fine,
            "keywords_treemap": keywords_treemap,
            "organization_publications": organization_publications,
            "organization_publications_by_research_area": organization_publications_by_research_area,
        }

    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def list(self, request):
        """Get dashboard data for a specific instance"""
        instance_id = request.query_params.get("instance")
        bin_size_param = request.query_params.get("bin_size", "0.5")

        if not instance_id:
            return Response(
                {"error": "instance parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            instance_id = int(instance_id)
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid instance parameter"},
                status=status.HTTP_400_BAD_REQUEST,
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
                "kpis": kpis,
                "charts": charts,
            }

            return Response(response_data)

        except Http404 as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @method_decorator(cache_page(60 * 30))  # Cache for 30 minutes
    @action(detail=False, methods=["get"])
    def general(self, request):
        """Get general conferences overview statistics"""
        venues = Venue.objects.all()
        instances = Instance.objects.select_related("venue").all()
        publications = Publication.objects.all()

        total_conferences = venues.count()
        total_papers = publications.count()
        years_covered = sorted(set(instances.values_list("year", flat=True)))
        avg_papers_per_year = total_papers / len(years_covered) if years_covered else 0

        # Conference summary
        conferences = []
        for venue in venues:
            venue_instances = instances.filter(venue=venue)
            venue_papers = publications.filter(instance__venue=venue).count()
            conferences.append(
                {
                    "name": venue.name,
                    "type": venue.type,
                    "instances": venue_instances.count(),
                    "total_papers": venue_papers,
                    "years": sorted(venue_instances.values_list("year", flat=True)),
                }
            )

        response_data = {
            "total_conferences": total_conferences,
            "total_papers": total_papers,
            "years_covered": years_covered,
            "avg_papers_per_year": round(avg_papers_per_year, 1),
            "conferences": conferences,
        }

        return Response(response_data)
