from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
import os
import requests
from .models import Category, Subcategory, Material
from api.database import SessionLocal, Component
from django.contrib.auth import logout

# 🔹 Views to render pages
def home(request):
    return render(request, 'reuse/home.html')

def upload_page(request):
    return render(request, 'reuse/upload.html')

def catalog(request):
    return render(request, 'reuse/catalog.html')

def api_view(request):
    return render(request, 'reuse/api.html')

def about(request):
    return render(request, 'reuse/about.html')


def upload_ifc_to_fastapi(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        project_name = request.POST.get('projectName', 'Default Project')
        location = request.POST.get('location', 'Unknown')

        # Prepare file and data
        files = {'file': (file.name, file.read(), file.content_type)}
        data = {
            'projectName': project_name,
            'location': location
        }

        # Send to FastAPI server
        response = requests.post('http://localhost:8001/upload/', files=files, data=data)

        try:
            return JsonResponse(response.json())
        except Exception as e:
            return JsonResponse({'error': 'Failed to parse FastAPI response', 'detail': str(e)})

    return render(request, 'reuse/upload.html')  # Or redirect to your upload form

@login_required
def settings_view(request):
    return render(request, 'reuse/settings.html')

def profile_view(request):
    return render(request, 'reuse/profile.html')

def logout_view(request):
    return redirect('logout')

def project_list(request):
    try:
        response = requests.get("http://127.0.0.1:8001/projects/")
        response.raise_for_status()
        projects = response.json()
    except Exception as e:
        projects = []
        error = f"Error fetching projects: {str(e)}"
        return render(request, "reuse/project_list.html", {"projects": projects, "error": error})

    return render(request, "reuse/project_list.html", {"projects": projects})

# views.py
from .models import Category, Subcategory

def catalog(request):
    # Load filters from GET
    selected_category = request.GET.get('category')
    selected_subcategory = request.GET.get('subcategory')
    selected_material = request.GET.get('material') or request.GET.get('material_other')
    location = request.GET.get('location')
    reuse_only = request.GET.get('reuse_only') == 'on'

    db = SessionLocal()
    query = db.query(Component)

    if selected_category:
        query = query.filter(Component.category == selected_category)
    if selected_subcategory:
        query = query.filter(Component.subcategory == selected_subcategory)
    if selected_material:
        query = query.filter(Component.material.ilike(f"%{selected_material}%"))
    if location:
        query = query.filter(Component.location.ilike(f"%{location}%"))
    if reuse_only:
        query = query.filter(Component.reuse_flag == True)

    components = query.all()
    db.close()

    return render(request, 'reuse/catalog.html', {
        'categories': Category.objects.all(),
        'subcategories': Subcategory.objects.all(),
        'materials': Material.objects.all(),
        'components': components,
        'selected': {
            'category': selected_category,
            'subcategory': selected_subcategory,
            'material': selected_material,
            'location': location,
            'reuse_only': reuse_only
        }
    })
