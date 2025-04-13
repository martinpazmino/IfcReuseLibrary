from django.shortcuts import render
from django.shortcuts import render
from django.http import JsonResponse
import os
from django.conf import settings

def home(request):
    return render(request, 'reuse/index.html')

def upload(request):
    return render(request, 'reuse/upload.html')

def catalog(request):
    return render(request, 'reuse/catalog.html')

def api_view(request):
    return render(request, 'reuse/api.html')

def about(request):
    return render(request, 'reuse/about.html')
def upload_ifc(request):
    if request.method == 'POST':
        project_name = request.POST.get('projectName')
        location = request.POST.get('location')
        file = request.FILES.get('file')

        if file:
            upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads")
            os.makedirs(upload_dir, exist_ok=True)

            file_path = os.path.join(upload_dir, file.name)
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            return JsonResponse({
                "message": "File uploaded successfully!",
                "filename": file.name
            })
        else:
            return JsonResponse({"message": "No file provided"}, status=400)

    return render(request, 'upload.html')