# projects/views.py
import requests
from django.shortcuts import render
from .forms import IFCFileUploadForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages


@login_required
def project_list(request):
    try:
        response = requests.get("http://127.0.0.1:8001/projects/")
        response.raise_for_status()
        projects = response.json()
    except Exception as e:
        projects = []
        error = f"Error fetching projects: {str(e)}"
        return render(request, "projects/projects_list.html", {"projects": projects, "error": error})

    return render(request, "projects/projects_list.html", {"projects": projects})

def upload_ifc(request):
    if request.method == 'POST':
        form = IFCFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            ifc_file = form.save(commit=False)
            ifc_file.user = request.user
            try:
                ifc_file.save()
                messages.success(request, "File uploaded successfully!")
                return redirect('project_list')
            except Exception as e:
                messages.error(request, f"Error saving file: {str(e)}")
        else:
            messages.error(request, "Invalid file. Please check the file type and size.")
    else:
        form = IFCFileUploadForm()
    return render(request, 'projects/upload_ifc.html', {'form': form})