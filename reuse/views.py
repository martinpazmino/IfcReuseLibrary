from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import os

# 🔹 Views to render pages
def home(request):
    return render(request, 'reuse/home.html')

def upload_page(request):
    return render(request, "reuse/upload.html")

def catalog(request):
    return render(request, 'reuse/catalog.html')

def api_view(request):
    return render(request, 'reuse/api.html')

def about(request):
    return render(request, 'reuse/about.html')


