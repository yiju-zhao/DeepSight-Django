from rest_framework import serializers

from .models import Event, Instance, Publication, Session, Venue


class VenueSerializer(serializers.ModelSerializer):
    """Serializer for Venue model"""

    class Meta:
        model = Venue
        fields = ["id", "name", "type", "description"]


class InstanceSerializer(serializers.ModelSerializer):
    """Serializer for Instance model"""

    venue = VenueSerializer(read_only=True)
    venue_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Instance
        fields = [
            "instance_id",
            "venue",
            "venue_id",
            "year",
            "start_date",
            "end_date",
            "location",
            "website",
            "summary",
        ]


class PublicationSerializer(serializers.ModelSerializer):
    """Serializer for Publication model"""

    instance = InstanceSerializer(read_only=True)
    instance_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Publication
        fields = [
            "id",
            "instance",
            "instance_id",
            "title",
            "authors",
            "aff",
            "aff_unique",
            "aff_country_unique",
            "author_position",
            "author_homepage",
            "abstract",
            "summary",
            "session",
            "rating",
            "keywords",
            "research_topic",
            "tag",
            "external_id",
            "doi",
            "pdf_url",
            "github",
            "site",
            "raw_file",
        ]


class PublicationTableSerializer(serializers.ModelSerializer):
    """Lightweight serializer for publication table display"""

    instance_year = serializers.IntegerField(source="instance.year", read_only=True)
    venue_name = serializers.CharField(source="instance.venue.name", read_only=True)

    class Meta:
        model = Publication
        fields = [
            "id",
            "title",
            "authors",
            "rating",
            "research_topic",
            "session",
            "aff_unique",
            "aff_country_unique",
            "keywords",
            "pdf_url",
            "github",
            "site",
            "instance_year",
            "venue_name",
            "abstract",
        ]


class EventSerializer(serializers.ModelSerializer):
    """Serializer for Event model"""

    instance = InstanceSerializer(read_only=True)
    instance_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "session_id",
            "instance",
            "instance_id",
            "title",
            "description",
            "abstract",
            "transcript",
            "expert_view",
            "ai_analysis",
        ]



class SessionSerializer(serializers.ModelSerializer):
    """Serializer for Session model"""

    instance = InstanceSerializer(read_only=True)
    instance_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Session
        fields = [
            "id",
            "instance",
            "instance_id",
            "date",
            "start_time",
            "end_time",
            "type",
            "title",
            "url",
            "speaker",
            "abstract",
            "overview",
            "transcript",
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


# ===== Import to Notebook Serializers =====


class ImportToNotebookRequestSerializer(serializers.Serializer):
    """Serializer for importing publications to notebook request"""

    publication_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="List of publication UUIDs to import",
    )
    notebook_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Existing notebook ID to import into (required if action is 'add')",
    )
    action = serializers.ChoiceField(
        choices=["add", "create"],
        default="add",
        help_text="Action to perform: 'add' to existing notebook or 'create' new one",
    )
    notebook_name = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=255,
        help_text="Name for new notebook (required if action is 'create')",
    )

    def validate(self, data):
        """Validate that required fields are present based on action"""
        action = data.get("action", "add")

        if action == "add":
            if not data.get("notebook_id"):
                raise serializers.ValidationError(
                    {"notebook_id": "notebook_id is required when action is 'add'"}
                )
        elif action == "create":
            if not data.get("notebook_name"):
                raise serializers.ValidationError(
                    {"notebook_name": "notebook_name is required when action is 'create'"}
                )

            # Check if notebook name already exists for this user
            from notebooks.models import Notebook

            user = self.context.get("request").user
            if Notebook.objects.filter(user=user, name=data["notebook_name"]).exists():
                raise serializers.ValidationError(
                    {"notebook_name": f"Notebook with name '{data['notebook_name']}' already exists"}
                )

        return data


class SkippedItemSerializer(serializers.Serializer):
    """Serializer for skipped publication items"""

    publication_id = serializers.UUIDField()
    title = serializers.CharField()
    reason = serializers.CharField()
    existing_item_id = serializers.UUIDField(required=False)


class ImportedItemSerializer(serializers.Serializer):
    """Serializer for successfully imported publication items"""

    publication_id = serializers.UUIDField()
    title = serializers.CharField()
    kb_item_id = serializers.UUIDField()
    url = serializers.CharField()


class FailedItemSerializer(serializers.Serializer):
    """Serializer for failed publication items"""

    publication_id = serializers.UUIDField()
    title = serializers.CharField()
    url = serializers.CharField()
    reason = serializers.CharField()


class ImportResponseSerializer(serializers.Serializer):
    """Serializer for import to notebook response"""

    success = serializers.BooleanField()
    total_requested = serializers.IntegerField()
    imported = serializers.IntegerField()
    failed = serializers.IntegerField()
    skipped = serializers.IntegerField()
    skipped_no_url = SkippedItemSerializer(many=True)
    skipped_duplicate = SkippedItemSerializer(many=True)
    successful_imports = ImportedItemSerializer(many=True)
    failed_imports = FailedItemSerializer(many=True)
    batch_job_id = serializers.UUIDField(allow_null=True)
    appended_to_batch = serializers.BooleanField()
    message = serializers.CharField()
    notebook_id = serializers.UUIDField(required=False)
    notebook_name = serializers.CharField(required=False)


class ActiveImportSerializer(serializers.Serializer):
    """Serializer for active import status"""

    batch_job_id = serializers.UUIDField()
    notebook_id = serializers.UUIDField()
    notebook_name = serializers.CharField()
    status = serializers.CharField()
    total_items = serializers.IntegerField()
    completed_items = serializers.IntegerField()
    failed_items = serializers.IntegerField()
    progress_percentage = serializers.FloatField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
