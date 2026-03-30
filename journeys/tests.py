from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Journey
import json
from .models import Journey, Expense
from unittest.mock import patch, MagicMock

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

class TravelogueExtendedTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a user and log them in
        self.user = User.objects.create_user(username='finance_test1', password='Password123!')
        self.client.login(username='finance_test1', password='Password123!')
        
        # Create a base Journey to attach expenses to
        self.journey = Journey.objects.create(
            user=self.user,
            title='Paris Trip',
            city='Paris',
            trip_date='2026-05-01',
            description='A lovely trip.'
        )

    def test_expense_tracker_flow(self):
        """Tests the full CRUD flow of the Expense Tracker."""
        expense_url = reverse('expense_tracker', args=[self.journey.id])
        
        # 1. Create an Expense
        expense_data = {
            'expenseDate': '2026-05-02',
            'category': 'Food',
            'amount': '45.50'
        }
        response = self.client.post(expense_url, expense_data)
        self.assertEqual(response.status_code, 302) # Redirects on success
        self.assertTrue(Expense.objects.filter(category='Food', amount='45.50').exists())

        # 2. Read the Expenses (Loads the dashboard)
        response = self.client.get(expense_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '45.50')

        # 3. Delete the Expense
        delete_url = reverse('expense_delete', kwargs={'journey_id': self.journey.id, 'expense_date': '2026-05-02'})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Expense.objects.filter(category='Food').exists())

    @patch('journeys.views.requests.post')
    @patch('journeys.views.geolocator.geocode')
    def test_surprise_me_aws_integration(self, mock_geocode, mock_post):
        """Tests the AWS Microservice integration without actually calling AWS."""
        
        # 1. Mock the Geocoder so we don't hit their API
        mock_geocode.return_value.latitude = 48.8566
        mock_geocode.return_value.longitude = 2.3522

        # 2. Mock the AWS API Gateway Response perfectly!
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "metadata": {"count": 1},
            "data": [
                {
                    "trip_data": {
                        "city": "Mockville",
                        "country": "Mockland",
                        "description": "A beautiful test destination."
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        # 3. Call the Surprise Me view
        surprise_url = reverse('surprise_me')
        response = self.client.get(surprise_url)

        # 4. Verify the view processed the "AWS" data correctly
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Expedition to Mockville')
        self.assertContains(response, 'Mockland')
        
        # Verify our code actually tried to call the API
        mock_post.assert_called_once()
    
    @patch('journeys.views.requests.post')
    def test_surprise_me_api_failure(self, mock_post):
        """SAD PATH: Tests if the app survives when the AWS API crashes."""
        import requests
        
        # 1. Force the mocked AWS server to throw a nasty Timeout Error
        mock_post.side_effect = requests.exceptions.RequestException("AWS Server is down!")
        
        # 2. Try to load the Surprise Me page
        surprise_url = reverse('surprise_me')
        response = self.client.get(surprise_url)
        
        # 3. Verify the app didn't crash (500), but gracefully redirected (302) to the timeline
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('journey_list'))

    @patch('journeys.views.requests.get')
    def test_available_consultations_loads(self, mock_get):
        """HAPPY PATH: Tests the Consultation API GET request."""
        # 1. Mock the API returning a valid time slot
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'slots': [{'id': 99, 'time': '14:00'}]}
        mock_get.return_value = mock_response

        # 2. Load the page
        url = reverse('available_consultations')
        response = self.client.get(url)

        # 3. Verify success
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '14:00')

    @patch('journeys.views.requests.post')
    def test_book_consultation_success(self, mock_post):
        """HAPPY PATH: Tests booking a consultation via the external API."""
        # 1. Mock a successful 200 OK booking response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # 2. Submit the booking POST request
        url = reverse('book_consultation', args=[99])
        response = self.client.post(url)

        # 3. Verify we get redirected to the "My Appointments" page
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('my_appointments'))