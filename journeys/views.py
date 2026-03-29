import requests
import random
from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login
from django import forms
from django.contrib import messages
from django.db.models import Sum
from .models import Journey, Expense
from geopy.geocoders import Nominatim

# --- CONFIGURATION ---
EMERGENCY_API_BASE = "https://api.anuragktech.me/api/services/"
APPOINTMENT_API_BASE = "https://2o7jj4hez6.execute-api.us-east-1.amazonaws.com"
APPOINTMENT_API_KEY = "1c1a99f9-a3bb-4b35-bd73-fc72aa4d483f"
DEFAULT_PROVIDER_ID = 4  
geolocator = Nominatim(user_agent="travelogue")


# ---------------------------
# Helper Functions
# ---------------------------
def get_opentripmap_data(lat, lon):
    """Helper function to fetch tourist spots from OpenTripMap"""
    API_KEY = "5ae2e3f221c38a28845f05b6773a26a8ad52cbaeec0ac46925812047"
    url = (
        f"https://api.opentripmap.com/0.1/en/places/radius?"
        f"radius=5000&lon={lon}&lat={lat}&"
        f"kinds=interesting_places&format=json&limit=10&apikey={API_KEY}"
    )
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            raw_data = response.json()
            return [
                {
                    'name': item.get('name'),
                    'type': item.get('kinds', 'Landmark').split(',')[0].replace('_', ' ').title(),
                    'lat': item.get('point', {}).get('lat'),
                    'lon': item.get('point', {}).get('lon')
                }
                for item in raw_data if item.get('name')
            ]
    except Exception as e:
        print(f"OpenTripMap Helper Error: {e}")
    return []


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
    weather_data = None 
    attractions = None 

    action = request.GET.get('action')
    user_lat = request.GET.get('lat')
    user_lon = request.GET.get('lon')

    if action == 'city' or (user_lat and user_lon):
        target_lat = None
        target_lon = None

        if user_lat and user_lon:
            target_lat, target_lon = user_lat, user_lon
            params = {"lat": user_lat, "lon": user_lon}
        else:
            if journey.latitude and journey.longitude:
                target_lat, target_lon = journey.latitude, journey.longitude
                params = {"lat": target_lat, "lon": target_lon}
            else:
                params = {"city": journey.city}

        # 1. Fetch Emergency Services (AWS API)
        try:
            response = requests.get(EMERGENCY_API_BASE, params=params, timeout=5)
            emergency_services = response.json() if response.status_code == 200 else []
        except requests.exceptions.RequestException:
            emergency_services = []

        # 2. Fetch Weather & Attractions 
        if target_lat and target_lon:
            try:
                w_url = "https://api.open-meteo.com/v1/forecast"
                w_params = {"latitude": target_lat, "longitude": target_lon, "current_weather": "true"}
                w_res = requests.get(w_url, params=w_params, timeout=3)
                if w_res.status_code == 200:
                    weather_data = w_res.json().get('current_weather') 
            except Exception:
                weather_data = None

            attractions = get_opentripmap_data(target_lat, target_lon)

    return render(request, 'journeys/journey_detail.html', {
        'journey': journey,
        'emergency_services': emergency_services,
        'weather_data': weather_data,
        'attractions': attractions,
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
# Expense Tracker Views (RDS Optimized)
# ---------------------------
@login_required
def expense_tracker(request, journey_id):
    journey = get_object_or_404(Journey, id=journey_id, user=request.user)
    
    # Handle Adding a New Expense
    if request.method == 'POST':
        expense_date = request.POST.get('expenseDate') or request.POST.get('date')
        category = request.POST.get('category')
        amount = request.POST.get('amount')
        
        Expense.objects.create(
            journey=journey,
            user=request.user,
            date=expense_date,
            category=category,
            amount=amount
        )
        return redirect('expense_tracker', journey_id=journey.id)

    # Fetch expenses for this specific journey
    expenses = journey.expenses.all().order_by('-date')
    
    # RDS Postgres Optimization
    aggregation = expenses.aggregate(total=Sum('amount'))
    total_spent = aggregation['total'] or 0.00 

    # Package for HTML
    expense_data = []
    for exp in expenses:
        expense_data.append({
            'expenseDate': exp.date,
            'category': exp.category,
            'amount': exp.amount
        })

    summary = {'total': f"{float(total_spent):.2f}"}

    return render(request, 'journeys/expense_tracker.html', {
        'journey': journey,
        'expenses': expense_data,
        'summary': summary,
    })

@login_required
def expense_delete(request, journey_id, expense_date):
    """Deletes an expense using Django ORM / RDS."""
    journey = get_object_or_404(Journey, id=journey_id, user=request.user)
    
    if request.method == 'POST':
        expense_to_delete = Expense.objects.filter(
            journey=journey, 
            user=request.user, 
            date=expense_date
        ).first()
        
        if expense_to_delete:
            expense_to_delete.delete()
            messages.success(request, "Expense deleted.")
            
    return redirect('expense_tracker', journey_id=journey.id)


# ---------------------------
# Consultation Views
# ---------------------------
@login_required
def available_consultations(request):
    target_date = request.GET.get('date', str(date.today()))
    headers = {'X-API-KEY': APPOINTMENT_API_KEY}
    params = {'provider_id': DEFAULT_PROVIDER_ID, 'date': target_date}
    
    try:
        response = requests.get(f"{APPOINTMENT_API_BASE}/slots/", params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            slots = response.json().get('slots', [])
        else:
            slots = []
    except Exception:
        slots = []
        messages.error(request, "Could not load slots. Check API connection.")

    return render(request, 'journeys/book_consultation.html', {'slots': slots, 'selected_date': target_date})

@login_required
def book_consultation(request, slot_id):
    if request.method == "POST":
        headers = {'X-API-KEY': APPOINTMENT_API_KEY, 'Content-Type': 'application/json'}
        payload = {
            "slot_id": slot_id,
            "customer_name": request.user.username,
            "customer_email": request.user.email
        }
        try:
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
    headers = {'X-API-KEY': APPOINTMENT_API_KEY}
    params = {'customer_email': request.user.email}
    try:
        response = requests.get(f"{APPOINTMENT_API_BASE}/appointments/", params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            user_appts = data.get('appointments', data.get('data', [])) if isinstance(data, dict) else data
        else:
            user_appts = []
    except Exception:
        user_appts = []
    return render(request, 'journeys/my_appointments.html', {'appointments': user_appts})


# ---------------------------
# Mock API / Surprise Me
# ---------------------------
FALLBACK_TRIPS = [
    {
        'title': 'Local Hidden Gem', 
        'city': 'Nearby Town', 
        'description': 'A beautiful spot right in your backyard!',
        'date': str(date.today()) 
    }
]

@login_required
def surprise_me(request):
    # 1. A curated vault of actual, amazing global destinations with pre-fetched coordinates.
    # This prevents Geocoding API timeouts and guarantees OpenTripMap has data!
    REAL_DESTINATIONS = [
        {'city': 'Kyoto', 'country': 'Japan', 'lat': 35.0116, 'lon': 135.7681},
        {'city': 'Reykjavik', 'country': 'Iceland', 'lat': 64.1466, 'lon': -21.9426},
        {'city': 'Florence', 'country': 'Italy', 'lat': 43.7695, 'lon': 11.2558},
        {'city': 'Marrakech', 'country': 'Morocco', 'lat': 31.6295, 'lon': -7.9811},
        {'city': 'Cape Town', 'country': 'South Africa', 'lat': -33.9249, 'lon': 18.4241},
        {'city': 'Cusco', 'country': 'Peru', 'lat': -13.5226, 'lon': -71.9673},
        {'city': 'Prague', 'country': 'Czechia', 'lat': 50.0755, 'lon': 14.4378},
        {'city': 'Hanoi', 'country': 'Vietnam', 'lat': 21.0285, 'lon': 105.8542},
        {'city': 'Edinburgh', 'country': 'Scotland', 'lat': 55.9533, 'lon': -3.1883},
        {'city': 'Cartagena', 'country': 'Colombia', 'lat': 10.3910, 'lon': -75.4794}
    ]

    travel_descriptions = [
        "A perfect getaway to capture some stunning photography. Explore the hidden streets and rich local culture.",
        "Immerse yourself in breathtaking landscapes. Make sure to bring your camera for this incredible adventure!",
        "From historical landmarks to vibrant local life, this destination offers endless opportunities to explore and unwind."
    ]

    suggested_trips = []
    
    # 2. Randomly select 3 unique destinations from our curated list
    chosen_spots = random.sample(REAL_DESTINATIONS, 3)

    for spot in chosen_spots:
        full_name = f"{spot['city']}, {spot['country']}"
        
        # 3. Fetch live attractions from OpenTripMap directly using the pre-baked coordinates
        attractions = []
        try:
            all_spots = get_opentripmap_data(spot['lat'], spot['lon'])
            attractions = all_spots[:3] if all_spots else []
        except Exception as e:
            print(f"OpenTripMap Error for {full_name}: {e}")

        # Generate a random future date within the next 6 months for the UI
        random_days = random.randint(14, 180)
        trip_date = date.today() + timedelta(days=random_days)

        # 4. Package the data for the template
        suggested_trips.append({
            'title': f"Expedition to {spot['city']}",
            'city': full_name,
            'description': random.choice(travel_descriptions),
            'date': str(trip_date),
            'attractions': attractions,
            'lat': spot['lat'],
            'lon': spot['lon']
        })

    return render(request, 'journeys/surprise_me.html', {'suggestions': suggested_trips})

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
def save_inspiration(request):
    """Catches the hidden form data and creates a new Journey."""
    if request.method == 'POST':
        # Create the Journey directly in your RDS Postgres Database
        new_journey = Journey.objects.create(
            user=request.user,
            title=request.POST.get('title'),
            city=request.POST.get('city'),
            description=request.POST.get('description'),
            trip_date=request.POST.get('trip_date'),
            latitude=request.POST.get('latitude'),
            longitude=request.POST.get('longitude')
        )
        
        # Add a success message and redirect them directly to their new trip dashboard!
        messages.success(request, f"Successfully saved {new_journey.city} to your timeline!")
        return redirect('journey_detail', id=new_journey.id)
        
    return redirect('surprise_me')
