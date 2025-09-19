from rest_framework import serializers
from .models import Venue, Instance, Publication, Event


class CommaSeparatedField(serializers.Field):
    """Custom field that splits comma-separated values into a list"""

    def __init__(self, max_items=None, **kwargs):
        self.max_items = max_items
        super().__init__(**kwargs)

    def to_representation(self, value):
        if not value:
            return []

        # Split by comma and filter out empty strings
        items = [item.strip() for item in value.split(',') if item.strip()]

        # Apply max_items limit if specified
        if self.max_items is not None:
            items = items[:self.max_items]

        return items

    def to_internal_value(self, data):
        if isinstance(data, list):
            return ','.join(str(item).strip() for item in data if str(item).strip())
        return str(data) if data else ''


class VenueSerializer(serializers.ModelSerializer):
    """Serializer for Venue model"""
    class Meta:
        model = Venue
        fields = ['id', 'name', 'type', 'description']


class InstanceSerializer(serializers.ModelSerializer):
    """Serializer for Instance model"""
    venue = VenueSerializer(read_only=True)
    venue_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Instance
        fields = [
            'instance_id', 'venue', 'venue_id', 'year',
            'start_date', 'end_date', 'location', 'website', 'summary'
        ]


class PublicationSerializer(serializers.ModelSerializer):
    """Serializer for Publication model"""
    instance = InstanceSerializer(read_only=True)
    instance_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Publication
        fields = [
            'id', 'instance', 'instance_id', 'title', 'authors',
            'aff', 'aff_unique', 'aff_country_unique',
            'author_position', 'author_homepage',
            'abstract', 'summary', 'session', 'rating',
            'keywords', 'research_topic', 'tag',
            'external_id', 'doi', 'pdf_url', 'github', 'site',
            'raw_file'
        ]


class PublicationTableSerializer(serializers.ModelSerializer):
    """Lightweight serializer for publication table display"""
    instance_year = serializers.IntegerField(source='instance.year', read_only=True)
    venue_name = serializers.CharField(source='instance.venue.name', read_only=True)

    # Use custom fields for comma-separated values
    authors_list = CommaSeparatedField(source='authors', read_only=True)
    countries_list = CommaSeparatedField(source='aff_country_unique', read_only=True)
    keywords_list = CommaSeparatedField(source='keywords', read_only=True)

    class Meta:
        model = Publication
        fields = [
            'id', 'title', 'authors', 'rating', 'research_topic',
            'session', 'aff_unique', 'aff_country_unique',
            'keywords', 'pdf_url', 'github', 'site',
            'instance_year', 'venue_name',
            # Add the new split fields
            'authors_list', 'countries_list', 'keywords_list'
        ]


class EventSerializer(serializers.ModelSerializer):
    """Serializer for Event model"""
    instance = InstanceSerializer(read_only=True)
    instance_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Event
        fields = [
            'id', 'session_id', 'instance', 'instance_id',
            'title', 'description', 'abstract', 'transcript',
            'expert_view', 'ai_analysis'
        ]


class DashboardKPISerializer(serializers.Serializer):
    """Serializer for dashboard KPI data"""
    total_publications = serializers.IntegerField()
    unique_authors = serializers.IntegerField()
    unique_affiliations = serializers.IntegerField()
    unique_countries = serializers.IntegerField()
    avg_rating = serializers.FloatField()
    session_distribution = serializers.DictField()
    author_position_distribution = serializers.DictField()
    resource_counts = serializers.DictField()


class DashboardChartSerializer(serializers.Serializer):
    """Serializer for dashboard chart data"""
    topics = serializers.ListField()
    top_affiliations = serializers.ListField()
    top_countries = serializers.ListField()
    top_keywords = serializers.ListField()
    ratings_histogram = serializers.ListField()
    session_types = serializers.ListField()
    author_positions = serializers.ListField()


class DashboardResponseSerializer(serializers.Serializer):
    """Serializer for complete dashboard response"""
    kpis = DashboardKPISerializer()
    charts = DashboardChartSerializer()
    table = PublicationTableSerializer(many=True)
    pagination = serializers.DictField()


class ConferenceOverviewSerializer(serializers.Serializer):
    """Serializer for conferences overview endpoint"""
    total_conferences = serializers.IntegerField()
    total_papers = serializers.IntegerField()
    years_covered = serializers.ListField()
    avg_papers_per_year = serializers.FloatField()
    conferences = serializers.ListField()