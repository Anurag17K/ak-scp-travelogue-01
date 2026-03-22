import requests
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login
from django import forms
from django.contrib import messages
from .models import Journey
from geopy.geocoders import Nominatim
from datetime import date

# --- CONFIGURATION ---
EMERGENCY_API_BASE = "https://api.anuragktech.me/api/services/"
APPOINTMENT_API_BASE = "http://api-env.eba-45cakfm9.us-east-1.elasticbeanstalk.com"
APPOINTMENT_API_KEY = "e7637b60-73c9-4406-9948-9e5d8154b918"
DEFAULT_PROVIDER_ID = 4  # Provider ID 
EXPENSE_API_BASE = "https://7xig37y0fj.execute-api.us-east-1.amazonaws.com/prod"

geolocator = Nominatim(user_agent="travelogue")

# ---------------------------
# Journey Views
# ---------------------------
@login_required
def journey_list(request):
    journeys = Journey.objects.filter(user=request.user)
    return render(request, 'journeys/journey_list.html', {'journeys': journeys})

@login_required
def journey_create(request):
    if request.method == 'POST':
        city = request.POST['city']
        location = geolocator.geocode(city)

        Journey.objects.create(
            user=request.user,
            title=request.POST['title'],
            trip_date=request.POST['trip_date'],
            description=request.POST['description'],
            city=city,
            latitude=location.latitude if location else None,
            longitude=location.longitude if location else None
        )
        return redirect('journey_list')
    return render(request, 'journeys/journey_form.html')

@login_required
def journey_detail(request, id):
    journey = get_object_or_404(Journey, id=id, user=request.user)
    emergency_services = None 
    weather_data = None  # NEW: Initialize weather data
    
    action = request.GET.get('action')
    user_lat = request.GET.get('lat')
    user_lon = request.GET.get('lon')

    if action == 'city' or (user_lat and user_lon):
        target_lat = None
        target_lon = None

        # Determine which coordinates to use
        if user_lat and user_lon:
            params = {"lat": user_lat, "lon": user_lon}
            target_lat, target_lon = user_lat, user_lon
        else:
            if journey.latitude and journey.longitude:
                params = {"lat": journey.latitude, "lon": journey.longitude}
                target_lat, target_lon = journey.latitude, journey.longitude
            else:
                params = {"city": journey.city}

        # 1. Fetch Emergency Services (AWS)
        try:
            response = requests.get(EMERGENCY_API_BASE, params=params, timeout=5)
            emergency_services = response.json() if response.status_code == 200 else []
        except requests.exceptions.RequestException:
            emergency_services = []

        # 2. NEW: Fetch Live Weather (Open-Meteo) using the same coordinates
        if target_lat and target_lon:
            try:
                weather_url = "https://api.open-meteo.com/v1/forecast"
                weather_params = {
                    "latitude": target_lat,
                    "longitude": target_lon,
                    "current_weather": "true" # Tells the API to return the current temp
                }
                w_response = requests.get(weather_url, params=weather_params, timeout=3)
                if w_response.status_code == 200:
                    # Extract just the current weather dictionary
                    weather_data = w_response.json().get('current_weather') 
            except Exception as e:
                print(f"Weather API Error: {e}")
                weather_data = None

    return render(request, 'journeys/journey_detail.html', {
        'journey': journey,
        'emergency_services': emergency_services,
        'weather_data': weather_data  # Pass it to the HTML template
    })

@login_required
def journey_update(request, id):
    journey = get_object_or_404(Journey, id=id, user=request.user)
    if request.method == 'POST':
        new_city = request.POST['city']
        if new_city != journey.city:
            location = geolocator.geocode(new_city)
            if location:
                journey.latitude = location.latitude
                journey.longitude = location.longitude

        journey.title = request.POST['title']
        journey.trip_date = request.POST['trip_date']
        journey.description = request.POST['description']
        journey.city = new_city
        journey.save()
        return redirect('journey_list')
    return render(request, 'journeys/journey_form.html', {'journey': journey})

@login_required
def journey_delete(request, id):
    journey = get_object_or_404(Journey, id=id, user=request.user)
    if request.method == 'POST':
        journey.delete()
        return redirect('journey_list')
    return render(request, 'journeys/journey_confirm_delete.html', {'journey': journey})

# ---------------------------
# Consultation Views (API Only)
# ---------------------------
@login_required
def available_consultations(request):
    """Shows slots based on the date selected by the user."""
    target_date = request.GET.get('date', str(date.today()))
    
    headers = {'X-API-KEY': APPOINTMENT_API_KEY}
    params = {'provider_id': DEFAULT_PROVIDER_ID, 'date': target_date}
    
    try:
        # REMOVED /api/ from the URL path here
        response = requests.get(f"{APPOINTMENT_API_BASE}/slots/", params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            slots = data.get('slots', [])
        else:
            print(f"API returned {response.status_code}: {response.text}")
            slots = []
            
    except Exception as e:
        print(f"Connection error: {e}")
        slots = []
        messages.error(request, "Could not load slots. Check API connection.")

    return render(request, 'journeys/book_consultation.html', {'slots': slots, 'selected_date': target_date})

@login_required
def book_consultation(request, slot_id):
    """Finalizes the booking for the user."""
    if request.method == "POST":
        headers = {'X-API-KEY': APPOINTMENT_API_KEY, 'Content-Type': 'application/json'}
        payload = {
            "slot_id": slot_id,
            "customer_name": request.user.username,
            "customer_email": request.user.email
        }
        
        try:
            # REMOVED /api/ from the URL path here
            response = requests.post(f"{APPOINTMENT_API_BASE}/book/", json=payload, headers=headers)
            if response.status_code in [200, 201]:
                messages.success(request, "Consultation booked! Check 'My Bookings'.")
                return redirect('my_appointments')
            else:
                messages.error(request, "Booking failed. Slot might be taken.")
        except Exception:
            messages.error(request, "API Error occurred.")

    return redirect('available_consultations')

@login_required
def my_appointments(request):
    """Fetches only the logged-in user's bookings directly from the API."""
    headers = {'X-API-KEY': APPOINTMENT_API_KEY}
    params = {'customer_email': request.user.email}
    
    try:
        # REMOVED /api/ from the URL path here
        response = requests.get(f"{APPOINTMENT_API_BASE}/appointments/", params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                user_appts = data.get('appointments', data.get('data', []))
            else:
                user_appts = data
        else:
            user_appts = []
            
    except Exception as e:
        print(f"Error fetching appointments: {e}")
        user_appts = []

    return render(request, 'journeys/my_appointments.html', {'appointments': user_appts})

# ---------------------------
# Auth Views
# ---------------------------
class SignUpForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)
    class Meta:
        model = User
        fields = ['username', 'email']
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("password2"):
            self.add_error('password2', "Passwords do not match")
        return cleaned_data

def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )
            login(request, user)
            return redirect('journey_list')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def expense_tracker(request):
    """Fetches the user's expense summary and list of expenses."""
    user_id = request.user.username  # Using Django username as API userId
    
    summary_data = {}
    expenses_data = []
    
    # 1. Fetch Summary
    try:
        res_summary = requests.get(f"{EXPENSE_API_BASE}/summary", params={"userId": user_id}, timeout=5)
        if res_summary.status_code == 200:
            summary_data = res_summary.json()
    except Exception as e:
        print(f"Summary API Error: {e}")
        messages.error(request, "Could not load expense summary.")

    # 2. Fetch Expenses List
    try:
        res_expenses = requests.get(f"{EXPENSE_API_BASE}/expense", params={"userId": user_id}, timeout=5)
        if res_expenses.status_code == 200:
            # Assuming the API returns a list or a dict with an 'expenses' key
            data = res_expenses.json()
            expenses_data = data.get('expenses', data) if isinstance(data, dict) else data
    except Exception as e:
        print(f"Expense API Error: {e}")
        messages.error(request, "Could not load expenses list.")

    return render(request, 'journeys/expense_tracker.html', {
        'summary': summary_data,
        'expenses': expenses_data
    })

@login_required
def expense_add(request):
    """Handles adding a new expense matching the specific API payload."""
    if request.method == 'POST':
        # Match the exact payload structure from the Network tab
        payload = {
            "userId": request.user.username,
            "expenseDate": request.POST.get('expenseDate', str(date.today())), # Grabs date from form, or defaults to today
            "category": request.POST.get('category'), 
            "amount": str(request.POST.get('amount')) # API expects this as a string
        }
        
        try:
            response = requests.post(f"{EXPENSE_API_BASE}/expense", json=payload, timeout=5)
            
            if response.status_code in [200, 201]:
                messages.success(request, "Expense added successfully!")
            else:
                messages.error(request, f"API Rejected: {response.text}")
        except Exception as e:
            messages.error(request, f"Connection Error: {str(e)}")
            
    return redirect('expense_tracker')

@login_required
def expense_delete(request, expense_date):
    """Handles deleting an expense using the required API payload."""
    if request.method == 'POST':
        # Matching the exact payload the API expects
        payload = {
            "userId": request.user.username,
            "expenseDate": expense_date
        }
        
        try:
            response = requests.delete(f"{EXPENSE_API_BASE}/expense", json=payload, timeout=5)
            
            if response.status_code == 200:
                messages.success(request, f"Expense from {expense_date} deleted.")
            else:
                messages.error(request, f"Failed to delete: {response.text}")
        except Exception as e:
            messages.error(request, "API Connection Error.")
            
    return redirect('expense_tracker')
    
@login_required
def surprise_me(request):
    suggested_trips = []
    schema = {"type": "trip", "count": 3}
    
    try:
        response = requests.post("https://mock-data-api-fk0f.onrender.com/generate/", json=schema, timeout=10)
        
        if response.status_code == 200:
            api_data = response.json().get('data', [])
            
            # --- ADD THIS DEBUG LINE ---
            if api_data:
                messages.info(request, f"RAW API DATA: {api_data[0]}")
            # ---------------------------

            for item in api_data:
                suggested_trips.append({
                    'title': item.get('title', 'Mystery Adventure'),
                    'city': item.get('location', 'Unknown City'),
                    'description': item.get('description', 'A wonderful surprise journey awaits!'),
                    'date': item.get('date', str(date.today()))
                })
        else:
            messages.error(request, "Our inspiration engine is currently taking a nap.")
            
    except Exception as e:
        messages.error(request, "Could not connect to the trip generator.")

    return render(request, 'journeys/surprise_me.html', {'suggestions': suggested_trips})