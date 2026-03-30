from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Journey
from unittest.mock import patch

class TravelogueIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        # URLs from your project/app urls.py
        self.signup_url = reverse('signup')
        self.login_url = '/accounts/login/' 
        self.create_url = reverse('journey_create')
        self.list_url = reverse('journey_list')

    def test_complete_user_flow(self):
        # 1. Signup Flow
        signup_payload = {
            'username': 'traveler_01',
            'email': 'traveler@nci.ie',
            'password': 'Password123!',
            'password2': 'Password123!'
        }
        response = self.client.post(self.signup_url, signup_payload)
        self.assertEqual(response.status_code, 302) # Redirects after signup
        self.assertTrue(User.objects.filter(username='traveler_01').exists())

        # 2. Login Flow (Django built-in)
        self.client.login(username='traveler_01', password='Password123!')

        # 3. Create Journey (Mocking geolocator to avoid external API calls)
        with patch('journeys.views.geolocator.geocode') as mocked_geo:
            mocked_geo.return_value.latitude = 53.3498
            mocked_geo.return_value.longitude = -6.2603

            journey_data = {
                'title': 'My Dublin Adventure',
                'trip_date': '2026-04-10',
                'description': 'Exploring the city center.',
                'city': 'Dublin'
            }
            response = self.client.post(self.create_url, journey_data)
            self.assertEqual(response.status_code, 302)
            
            # Verify it exists in RDS (Local Test DB)
            journey = Journey.objects.get(title='My Dublin Adventure')
            self.assertEqual(journey.city, 'Dublin')

        # 4. Read (Timeline View)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Dublin Adventure')

        # 5. Delete Journey
        delete_url = reverse('journey_delete', args=[journey.id])
        response = self.client.post(delete_url) # View handles deletion on POST
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Journey.objects.filter(id=journey.id).exists())