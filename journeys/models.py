from django.db import models
from django.contrib.auth.models import User

class Journey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    trip_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.title