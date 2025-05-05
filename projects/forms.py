# projects/forms.py
from django import forms
from .models import IFCFile

class IFCFileUploadForm(forms.ModelForm):
    class Meta:
        model = IFCFile
        fields = ['file']

    def clean_file(self):
        file = self.cleaned_data['file']
        if not file.name.endswith('.ifc'):
            raise forms.ValidationError("Only .ifc files are allowed.")
        if file.size > 10 * 1024 * 1024:  # 10MB Limit
            raise forms.ValidationError("File size must be under 10MB.")
        return file