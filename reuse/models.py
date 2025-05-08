# reuse/models.py
from django.db import models

class Component(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=100)

    class Meta:
        managed = False  # This model won't create/alter the table
        db_table = 'components'
