from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Journey
from django.contrib.auth.models import User
from django.contrib.auth import login
from django import forms

@login_required
def journey_list(request):
    journeys = Journey.objects.filter(user=request.user)
    return render(request, 'journeys/journey_list.html', {'journeys': journeys})


@login_required
def journey_create(request):
    if request.method == 'POST':
        Journey.objects.create(
            user=request.user,
            title=request.POST['title'],
            trip_date=request.POST['trip_date'],
            description=request.POST['description'],
            theme=request.POST['theme']
        )
        return redirect('journey_list')
    return render(request, 'journeys/journey_form.html')


@login_required
def journey_update(request, id):
    journey = get_object_or_404(Journey, id=id, user=request.user)

    if request.method == 'POST':
        journey.title = request.POST['title']
        journey.trip_date = request.POST['trip_date']
        journey.description = request.POST['description']
        journey.theme = request.POST['theme']
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

# Simple signup form
class SignUpForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password2 = cleaned_data.get("password2")
        if password and password2 and password != password2:
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
            login(request, user)  # automatically log the user in
            return redirect('journey_list')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})
