# accounts/views.py
from django.shortcuts import render, redirect
from .forms import UserRegistrationForm
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.http import JsonResponse
import jwt
from datetime import datetime, timedelta
from django.conf import settings

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)
            messages.success(request, "Registration successful!")
            return redirect('home')  # Ersetze 'home' durch deine Ziel-URL
        else:
            messages.error(request, "Registration failed. Please check your input.")
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

def generate_token(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Generiere JWT
            payload = {
                'user_id': user.id,
                'exp': datetime.utcnow() + timedelta(hours=24),
                'iat': datetime.utcnow()
            }
            token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
            return JsonResponse({'token': token})
        else:
            return JsonResponse({'error': 'Invalid credentials'}, status=401)
    return JsonResponse({'error': 'Invalid request'}, status=400)

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')  # Ersetze 'home' durch deine Ziel-URL
        else:
            messages.error(request, "Invalid username or password")
    return render(request, 'accounts/login.html')