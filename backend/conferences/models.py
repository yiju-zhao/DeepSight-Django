import uuid
from django.db import models
from storages.backends.s3boto3 import S3Boto3Storage

def publication_file_path(instance, filename):
    """
    e.g. publications/CVPR/2017/3303/3D_Bounding_Box_Estimation.pdf
    """
    venue   = instance.instance.venue.name.replace(" ", "_")
    year    = instance.instance.year
    pid     = instance.id or "new"
    return f"publications/{venue}/{year}/{pid}/{filename}"

class Venue(models.Model):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Instance(models.Model):
    instance_id = models.AutoField(primary_key=True)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='instances')
    year = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    location = models.CharField(max_length=255)
    website = models.CharField(max_length=255)
    summary = models.TextField()

    def __str__(self):
        return f"{self.venue.name} {self.year}"

    class Meta:
        ordering = ['-year', 'venue__name']
        indexes = [
            models.Index(fields=['venue', 'year']),
            models.Index(fields=['year']),
        ]


class Publication(models.Model):
    # Primary key and relationships
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instance = models.ForeignKey(Instance, on_delete=models.CASCADE, related_name='publications')

    # Core publication information
    title = models.CharField(max_length=255)
    authors = models.CharField(max_length=255)
    aff = models.CharField(max_length=255)
    aff_unique = models.CharField(max_length=500, blank=True, null=True)
    aff_country_unique = models.CharField(max_length=255, blank=True, null=True)
    author_position = models.CharField(max_length=500, blank=True, null=True)
    author_homepage = models.CharField(max_length=1000, blank=True, null=True)
    abstract = models.TextField()
    summary = models.TextField()
    session = models.CharField(max_length=255, blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)

    # Publication metadata
    keywords = models.CharField(max_length=500)
    research_topic = models.CharField(max_length=500)
    tag = models.CharField(max_length=255)

    # External identifiers and links
    external_id = models.CharField(max_length=255, blank=True, null=True)
    doi = models.CharField(max_length=255)
    pdf_url = models.CharField(max_length=255)
    github = models.URLField(blank=True, null=True)
    site = models.URLField(blank=True, null=True)

    # File storage
    raw_file = models.FileField(
        upload_to=publication_file_path,
        storage=S3Boto3Storage(),
        blank=True,
        null=True,
        help_text="PDF file stored in MinIO",
    )


    def __str__(self):
        return self.title

    class Meta:
        ordering = ['title']
        indexes = [
            models.Index(fields=['instance']),
            models.Index(fields=['instance', 'research_topic']),
            models.Index(fields=['session']),
            models.Index(fields=['rating']),
        ]


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.IntegerField()
    instance = models.ForeignKey(Instance, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=255)
    description = models.TextField()
    abstract = models.TextField()
    transcript = models.TextField()
    expert_view = models.TextField()
    ai_analysis = models.TextField()

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['session_id', 'title']
