from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, datetime
import json

from .models import Venue, Instance, Publication, Event

User = get_user_model()


class ConferencesAPITestCase(APITestCase):
    """Base test case for conferences API tests"""

    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create test venue
        self.venue = Venue.objects.create(
            name='CVPR',
            type='Conference',
            description='Computer Vision and Pattern Recognition'
        )

        # Create test instance
        self.instance = Instance.objects.create(
            venue=self.venue,
            year=2023,
            start_date=date(2023, 6, 17),
            end_date=date(2023, 6, 21),
            location='Vancouver, Canada',
            website='https://cvpr2023.thecvf.com/',
            summary='Leading conference in computer vision'
        )

        # Create test publications
        self.publication1 = Publication.objects.create(
            instance=self.instance,
            title='Deep Learning for Computer Vision',
            authors='John Doe;Jane Smith',
            aff='MIT;Stanford University',
            aff_unique='MIT;Stanford',
            aff_country_unique='United States',
            author_position='PhD student;Professor',
            author_homepage='https://johndoe.com;https://janesmith.edu',
            abstract='This paper presents a novel approach...',
            summary='Novel deep learning method',
            session='Oral',
            rating=8.5,
            keywords='deep learning;computer vision;neural networks',
            research_topic='Machine Learning',
            tag='main',
            external_id='paper123',
            doi='10.1000/182',
            pdf_url='https://example.com/paper.pdf',
            github='https://github.com/example/repo',
            site='https://project-site.com'
        )

        self.publication2 = Publication.objects.create(
            instance=self.instance,
            title='Image Recognition with Transformers',
            authors='Bob Wilson',
            aff='Google',
            aff_unique='Google',
            aff_country_unique='United States',
            author_position='Research Scientist',
            abstract='Transformers for image recognition...',
            summary='Transformer-based image recognition',
            session='Poster',
            rating=7.2,
            keywords='transformers;image recognition',
            research_topic='Computer Vision',
            tag='main',
            external_id='paper456',
            doi='10.1000/183',
            pdf_url='https://example.com/paper2.pdf'
        )

        # Create test event
        self.event = Event.objects.create(
            instance=self.instance,
            session_id=1,
            title='Opening Keynote',
            description='Welcome to CVPR 2023',
            abstract='Overview of recent advances',
            transcript='Welcome everyone...',
            expert_view='Excellent presentation',
            ai_analysis='Positive sentiment detected'
        )

    def authenticate(self):
        """Authenticate the test client"""
        self.client.force_authenticate(user=self.user)


class VenueViewSetTest(ConferencesAPITestCase):
    """Test VenueViewSet"""

    def test_list_venues_requires_auth(self):
        """Test that listing venues requires authentication"""
        url = reverse('venue-list')
        response = self.client.get(url)
        # DRF returns 403 for unauthenticated requests when IsAuthenticated is used
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_venues_authenticated(self):
        """Test listing venues when authenticated"""
        self.authenticate()
        url = reverse('venue-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if response is paginated or not
        if 'results' in response.data:
            venues = response.data['results']
        else:
            venues = response.data
        self.assertGreaterEqual(len(venues), 1)
        # Check that our test venue exists
        venue_names = [venue['name'] for venue in venues]
        self.assertIn('CVPR', venue_names)

    def test_create_venue(self):
        """Test creating a new venue"""
        self.authenticate()
        url = reverse('venue-list')
        initial_count = Venue.objects.count()
        data = {
            'name': 'ICCV',
            'type': 'Conference',
            'description': 'International Conference on Computer Vision'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Venue.objects.count(), initial_count + 1)


class InstanceViewSetTest(ConferencesAPITestCase):
    """Test InstanceViewSet"""

    def test_list_instances(self):
        """Test listing instances"""
        self.authenticate()
        url = reverse('instance-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if response is paginated or not
        if 'results' in response.data:
            instances = response.data['results']
        else:
            instances = response.data
        self.assertGreaterEqual(len(instances), 1)

    def test_filter_instances_by_venue(self):
        """Test filtering instances by venue name"""
        self.authenticate()
        url = reverse('instance-list')
        response = self.client.get(url, {'venue': 'CVPR'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if response is paginated or not
        if 'results' in response.data:
            instances = response.data['results']
        else:
            instances = response.data
        self.assertGreaterEqual(len(instances), 1)

        # Test with non-existent venue
        response = self.client.get(url, {'venue': 'NONEXISTENT'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if 'results' in response.data:
            instances = response.data['results']
        else:
            instances = response.data
        self.assertEqual(len(instances), 0)


class PublicationViewSetTest(ConferencesAPITestCase):
    """Test PublicationViewSet"""

    def test_list_publications(self):
        """Test listing publications"""
        self.authenticate()
        url = reverse('publication-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_filter_publications_by_instance(self):
        """Test filtering publications by instance"""
        self.authenticate()
        url = reverse('publication-list')
        response = self.client.get(url, {'instance': self.instance.instance_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_publication_detail(self):
        """Test getting publication detail"""
        self.authenticate()
        url = reverse('publication-detail', args=[self.publication1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Deep Learning for Computer Vision')


class DashboardViewSetTest(ConferencesAPITestCase):
    """Test DashboardViewSet"""

    def test_dashboard_requires_auth(self):
        """Test that dashboard requires authentication"""
        url = reverse('dashboard-dashboard')
        response = self.client.get(url)
        # DRF returns 403 for unauthenticated requests when IsAuthenticated is used
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_missing_parameters(self):
        """Test dashboard with missing parameters"""
        self.authenticate()
        url = reverse('dashboard-dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_dashboard_with_venue_and_year(self):
        """Test dashboard with venue and year parameters"""
        self.authenticate()
        url = reverse('dashboard-dashboard')
        response = self.client.get(url, {'venue': 'CVPR', 'year': 2023})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check response structure
        self.assertIn('kpis', response.data)
        self.assertIn('charts', response.data)
        self.assertIn('table', response.data)
        self.assertIn('pagination', response.data)

        # Check KPIs
        kpis = response.data['kpis']
        self.assertEqual(kpis['total_publications'], 2)
        self.assertEqual(kpis['unique_authors'], 3)  # John Doe, Jane Smith, Bob Wilson
        self.assertTrue(kpis['avg_rating'] > 0)
        self.assertIn('session_distribution', kpis)
        self.assertIn('author_position_distribution', kpis)

    def test_dashboard_with_instance(self):
        """Test dashboard with instance parameter"""
        self.authenticate()
        url = reverse('dashboard-dashboard')
        response = self.client.get(url, {'instance': self.instance.instance_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should have same results as venue/year test
        kpis = response.data['kpis']
        self.assertEqual(kpis['total_publications'], 2)

    def test_dashboard_charts_data(self):
        """Test dashboard charts data structure"""
        self.authenticate()
        url = reverse('dashboard-dashboard')
        response = self.client.get(url, {'venue': 'CVPR', 'year': 2023})

        charts = response.data['charts']
        self.assertIn('topics', charts)
        self.assertIn('top_affiliations', charts)
        self.assertIn('top_countries', charts)
        self.assertIn('top_keywords', charts)
        self.assertIn('ratings_histogram', charts)
        self.assertIn('session_types', charts)
        self.assertIn('author_positions', charts)

        # Check data format
        self.assertIsInstance(charts['topics'], list)
        if charts['topics']:
            self.assertIn('name', charts['topics'][0])
            self.assertIn('count', charts['topics'][0])

    def test_dashboard_kpis_calculation(self):
        """Test KPIs calculation accuracy"""
        self.authenticate()
        url = reverse('dashboard-dashboard')
        response = self.client.get(url, {'venue': 'CVPR', 'year': 2023})

        kpis = response.data['kpis']

        # Check session distribution
        session_dist = kpis['session_distribution']
        self.assertEqual(session_dist.get('Oral', 0), 1)
        self.assertEqual(session_dist.get('Poster', 0), 1)

        # Check resource counts
        resource_counts = kpis['resource_counts']
        self.assertEqual(resource_counts['with_github'], 1)  # Only publication1 has GitHub
        self.assertEqual(resource_counts['with_pdf'], 2)  # Both have PDF URLs

    def test_overview_endpoint(self):
        """Test conferences overview endpoint"""
        self.authenticate()
        url = reverse('dashboard-overview')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIn('total_conferences', data)
        self.assertIn('total_papers', data)
        self.assertIn('years_covered', data)
        self.assertIn('avg_papers_per_year', data)
        self.assertIn('conferences', data)

        self.assertEqual(data['total_conferences'], 1)
        self.assertEqual(data['total_papers'], 2)
        self.assertIn(2023, data['years_covered'])


class DataAggregationTest(ConferencesAPITestCase):
    """Test data aggregation logic"""

    def test_semicolon_separated_authors(self):
        """Test handling of semicolon-separated authors"""
        self.authenticate()
        url = reverse('dashboard-dashboard')
        response = self.client.get(url, {'venue': 'CVPR', 'year': 2023})

        kpis = response.data['kpis']
        # Should correctly count John Doe, Jane Smith, Bob Wilson = 3 unique authors
        self.assertEqual(kpis['unique_authors'], 3)

    def test_author_position_aggregation(self):
        """Test author position aggregation"""
        self.authenticate()
        url = reverse('dashboard-dashboard')
        response = self.client.get(url, {'venue': 'CVPR', 'year': 2023})

        kpis = response.data['kpis']
        position_dist = kpis['author_position_distribution']

        # Should have PhD student, Professor, Research Scientist
        self.assertIn('PhD student', position_dist)
        self.assertIn('Professor', position_dist)
        self.assertIn('Research Scientist', position_dist)

    def test_keywords_aggregation(self):
        """Test keywords aggregation in charts"""
        self.authenticate()
        url = reverse('dashboard-dashboard')
        response = self.client.get(url, {'venue': 'CVPR', 'year': 2023})

        charts = response.data['charts']
        keywords = charts['top_keywords']

        # Should include keywords from both publications
        keyword_names = [kw['name'] for kw in keywords]
        self.assertIn('deep learning', keyword_names)
        self.assertIn('computer vision', keyword_names)
        self.assertIn('transformers', keyword_names)


class PaginationTest(ConferencesAPITestCase):
    """Test pagination functionality"""

    def test_publication_pagination(self):
        """Test publication list pagination"""
        self.authenticate()
        url = reverse('publication-list')
        response = self.client.get(url, {'page_size': 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertEqual(response.data['count'], 2)


class ModelTest(TestCase):
    """Test model methods and properties"""

    def setUp(self):
        self.venue = Venue.objects.create(
            name='ICCV',
            type='Conference',
            description='International Conference on Computer Vision'
        )

        self.instance = Instance.objects.create(
            venue=self.venue,
            year=2023,
            start_date=date(2023, 10, 1),
            end_date=date(2023, 10, 5),
            location='Paris, France',
            website='https://iccv2023.thecvf.com/',
            summary='Top computer vision conference'
        )

    def test_venue_str(self):
        """Test Venue string representation"""
        self.assertEqual(str(self.venue), 'ICCV')

    def test_instance_str(self):
        """Test Instance string representation"""
        self.assertEqual(str(self.instance), 'ICCV 2023')

    def test_publication_file_path(self):
        """Test publication file path generation"""
        from .models import publication_file_path

        publication = Publication.objects.create(
            instance=self.instance,
            title='Test Publication',
            authors='Test Author',
            aff='Test University',
            abstract='Test abstract',
            summary='Test summary',
            keywords='test',
            research_topic='Test Topic',
            tag='main',
            doi='10.1000/test',
            pdf_url='https://example.com/test.pdf'
        )

        file_path = publication_file_path(publication, 'test.pdf')
        expected_path = f"publications/ICCV/2023/{publication.id}/test.pdf"
        self.assertEqual(file_path, expected_path)