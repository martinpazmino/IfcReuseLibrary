from django.contrib import admin

# Register your models here.
# admin.py
from .models import Category, Subcategory, Material

admin.site.register(Category)
admin.site.register(Subcategory)
admin.site.register(Material)