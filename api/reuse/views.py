from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import os

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
        response = requests.post('http://localhost:8001/upload', files=files, data=data)

        try:
            return JsonResponse(response.json())
        except Exception as e:
            return JsonResponse({'error': 'Failed to parse FastAPI response', 'detail': str(e)})

    return render(request, 'reuse/upload.html')  # Or redirect to your upload form
