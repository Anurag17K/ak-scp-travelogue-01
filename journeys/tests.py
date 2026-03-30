import json
import requests
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Journey, Expense
from unittest.mock import patch, MagicMock

# ==========================================
# 1. CORE INTEGRATION TEST (The User Journey)
# ==========================================
class TravelogueIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.signup_url = reverse('signup')
        self.login_url = '/accounts/login/' 
        self.create_url = reverse('journey_create')
        self.list_url = reverse('journey_list')

    def test_complete_user_flow(self):
        # 1. Signup
        signup_payload = {
            'username': 'traveler_01',
            'email': 'traveler@nci.ie',
            'password': 'Password123!',
            'password2': 'Password123!'
        }
        response = self.client.post(self.signup_url, signup_payload)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='traveler_01').exists())

        # 2. Login
        self.client.login(username='traveler_01', password='Password123!')

        # 3. Create Journey
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
            
            journey = Journey.objects.get(title='My Dublin Adventure')
            self.assertEqual(journey.city, 'Dublin')

        # 4. Read Timeline
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Dublin Adventure')


# ==========================================
# 2. ISOLATED CRUD TESTS (High Coverage)
# ==========================================
class JourneyCRUDTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='tester', password='Password123!')
        self.client.login(username='tester', password='Password123!')
        
        self.journey = Journey.objects.create(
            user=self.user,
            title='Initial Trip',
            city='Old City',
            description='Just a test.',
            latitude=10.0,
            longitude=20.0
        )

    @patch('journeys.views.geolocator.geocode')
    def test_journey_create_view(self, mock_geocode):
        mock_location = MagicMock()
        mock_location.latitude = 53.3498
        mock_location.longitude = -6.2603
        mock_geocode.return_value = mock_location

        create_url = reverse('journey_create')
        response = self.client.post(create_url, {
            'title': 'New Dublin Trip',
            'trip_date': '2026-06-01',
            'description': 'Exploring Temple Bar.',
            'city': 'Dublin'
        })

        self.assertRedirects(response, reverse('journey_list'))
        self.assertTrue(Journey.objects.filter(title='New Dublin Trip').exists())

    @patch('journeys.views.get_opentripmap_data')
    @patch('journeys.views.requests.get')
    def test_journey_detail_view(self, mock_requests_get, mock_otm):
        mock_api_response = MagicMock()
        mock_api_response.status_code = 200
        mock_api_response.json.return_value = {"current_weather": {"temperature": 15.0}}
        mock_requests_get.return_value = mock_api_response

        mock_otm.return_value = [{'name': 'Fake Castle', 'type': 'Landmark'}]

        detail_url = reverse('journey_detail', args=[self.journey.id])
        response = self.client.get(detail_url, {'action': 'city'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('journey', response.context)
        self.assertIn('weather_data', response.context)

    @patch('journeys.views.geolocator.geocode')
    def test_journey_update_view_new_city(self, mock_geocode):
        mock_location = MagicMock()
        mock_location.latitude = 48.8566
        mock_location.longitude = 2.3522
        mock_geocode.return_value = mock_location

        update_url = reverse('journey_update', args=[self.journey.id])
        response = self.client.post(update_url, {
            'title': 'Updated Trip to Paris',
            'trip_date': '2026-07-14',
            'description': 'Bastille Day!',
            'city': 'Paris'
        })

        self.assertRedirects(response, reverse('journey_list'))
        self.journey.refresh_from_db()
        self.assertEqual(self.journey.city, 'Paris')

    def test_journey_delete_view(self):
        delete_url = reverse('journey_delete', args=[self.journey.id])
        response = self.client.post(delete_url)
        self.assertRedirects(response, reverse('journey_list'))
        self.assertFalse(Journey.objects.filter(id=self.journey.id).exists())


# ==========================================
# 3. EXTENDED FEATURES & API TESTS
# ==========================================
class TravelogueExtendedTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='finance_test1', password='Password123!')
        self.client.login(username='finance_test1', password='Password123!')
        
        self.journey = Journey.objects.create(
            user=self.user,
            title='Paris Trip',
            city='Paris',
            trip_date='2026-05-01',
            description='A lovely trip.'
        )

    def test_expense_tracker_flow(self):
        expense_url = reverse('expense_tracker', args=[self.journey.id])
        
        expense_data = {
            'expenseDate': '2026-05-02',
            'category': 'Food',
            'amount': '45.50'
        }
        response = self.client.post(expense_url, expense_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Expense.objects.filter(category='Food', amount='45.50').exists())

        response = self.client.get(expense_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '45.50')

        delete_url = reverse('expense_delete', kwargs={'journey_id': self.journey.id, 'expense_date': '2026-05-02'})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Expense.objects.filter(category='Food').exists())

    @patch('journeys.views.requests.post')
    @patch('journeys.views.geolocator.geocode')
    def test_surprise_me_aws_integration(self, mock_geocode, mock_post):
        mock_geocode.return_value.latitude = 48.8566
        mock_geocode.return_value.longitude = 2.3522

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

        surprise_url = reverse('surprise_me')
        response = self.client.get(surprise_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Expedition to Mockville')
        mock_post.assert_called_once()
    
    @patch('journeys.views.requests.post')
    def test_surprise_me_api_failure(self, mock_post):
        mock_post.side_effect = requests.exceptions.RequestException("AWS Server is down!")
        
        surprise_url = reverse('surprise_me')
        response = self.client.get(surprise_url)
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('journey_list'))

    @patch('journeys.views.requests.get')
    def test_available_consultations_loads(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        # FIX APPLIED: Used 'slot_id' to match the HTML template expectation
        mock_response.json.return_value = {'slots': [{'slot_id': 99, 'time': '14:00'}]}
        mock_get.return_value = mock_response

        url = reverse('available_consultations')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '14:00')

    @patch('journeys.views.requests.post')
    def test_book_consultation_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        url = reverse('book_consultation', args=[99])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('my_appointments'))