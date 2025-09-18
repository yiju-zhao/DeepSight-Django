from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register viewsets
router = DefaultRouter(trailing_slash=True)
router.register(r'venues', views.VenueViewSet, basename='venue')
router.register(r'instances', views.InstanceViewSet, basename='instance')
router.register(r'publications', views.PublicationViewSet, basename='publication')
router.register(r'events', views.EventViewSet, basename='event')
router.register(r'dashboard', views.DashboardViewSet, basename='dashboard')

# URL patterns
urlpatterns = [
    path('', include(router.urls)),
]

# Available endpoints:
# /api/v1/conferences/venues/ (list/detail)
# /api/v1/conferences/instances/ (list/detail; support ?venue=CVPR)
# /api/v1/conferences/publications/ (list/detail; support ?instance=<id>)
# /api/v1/conferences/events/ (list/detail; support ?instance=<id>)
# /api/v1/conferences/dashboard/dashboard/ (dashboard analytics)
# /api/v1/conferences/dashboard/overview/ (conferences overview)