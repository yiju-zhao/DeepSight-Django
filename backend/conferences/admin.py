from django.contrib import admin
from .models import Venue, Instance, Publication, Event

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'description')
    search_fields = ('name', 'type')
    list_filter = ('type',)

@admin.register(Instance)
class InstanceAdmin(admin.ModelAdmin):
    list_display = ('venue', 'year', 'location', 'start_date', 'end_date')
    search_fields = ('venue__name', 'location')
    list_filter = ('year', 'venue__type')
    date_hierarchy = 'start_date'

@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ('title', 'authors', 'instance', 'rating', 'external_id')
    search_fields = ('title', 'authors', 'keywords', 'research_topic', 'external_id', 'aff', 'aff_unique')
    list_filter = ('instance__venue', 'instance__year', 'tag', 'session', 'aff_country_unique')
    readonly_fields = ('id',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'instance', 'title', 'authors')
        }),
        ('Author Details', {
            'fields': ('author_position', 'author_homepage')
        }),
        ('Affiliations', {
            'fields': ('aff', 'aff_unique', 'aff_country_unique')
        }),
        ('Content', {
            'fields': ('abstract', 'summary', 'session', 'rating')
        }),
        ('Metadata', {
            'fields': ('keywords', 'research_topic', 'tag')
        }),
        ('External Links', {
            'fields': ('external_id', 'doi', 'pdf_url', 'github', 'site')
        }),
        ('File Storage', {
            'fields': ('raw_file',)
        }),
    )

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'session_id', 'instance', 'description')
    search_fields = ('title', 'description', 'abstract')
    list_filter = ('instance__venue', 'instance__year')
    readonly_fields = ('id',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'session_id', 'instance', 'title')
        }),
        ('Content', {
            'fields': ('description', 'abstract', 'transcript')
        }),
        ('Analysis', {
            'fields': ('expert_view', 'ai_analysis')
        }),
    )
