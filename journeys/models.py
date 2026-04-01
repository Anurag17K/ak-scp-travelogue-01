from django.db import models
from django.contrib.auth.models import User
from PIL import Image, ExifTags

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
    
class Expense(models.Model):
    # This links the expense to a specific trip
    journey = models.ForeignKey('Journey', on_delete=models.CASCADE, related_name='expenses')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    category = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.category} - {self.amount}"
    
class JourneyMedia(models.Model):
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='media_gallery')
    image = models.ImageField(upload_to='journey_media/')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.image and not self.pk:
            try:
                img = Image.open(self.image)
                exif = {ExifTags.TAGS[k]: v for k, v in img._getexif().items() if k in ExifTags.TAGS}
                if 'GPSInfo' in exif:
                    gps = exif['GPSInfo']
                    def to_deg(v): return float(v[0]) + (float(v[1]) / 60.0) + (float(v[2]) / 3600.0)
                    lat, lon = to_deg(gps[2]), to_deg(gps[4])
                    if gps[1] == 'S': lat = -lat
                    if gps[3] == 'W': lon = -lon
                    self.latitude, self.longitude = lat, lon
            except Exception:
                pass 
        super().save(*args, **kwargs)