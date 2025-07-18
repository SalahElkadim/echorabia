from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime
from cloudinary.models import CloudinaryField
import os



class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('owner', 'Owner'),
        ('customer', 'Customer')
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="customer")
    def __str__(self):
        return f"{self.username} ({self.role})"


class ServiceBooking(models.Model):
    # استخدام CloudinaryField للصور والفيديوهات
    if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('PRODUCTION'):
        image1 = CloudinaryField('image', folder='ServiceImages/', blank=True, null=True)
        image2 = CloudinaryField('image', folder='ServiceImages/', blank=True, null=True)
        image3 = CloudinaryField('image', folder='ServiceImages/', blank=True, null=True)
        video = CloudinaryField('video', folder='videos/', blank=True, null=True)
    else:
        # للتطوير المحلي
        image1 = models.ImageField(upload_to='ServiceImages/', blank=True, null=True)
        image2 = models.ImageField(upload_to='ServiceImages/', blank=True, null=True)
        image3 = models.ImageField(upload_to='ServiceImages/', blank=True, null=True)
        video = models.FileField(upload_to='videos/', blank=True, null=True)
    
    title = models.CharField(max_length=50)
    description = models.TextField()
    included = models.TextField(default="", blank=True, null=True)
    exclusion = models.TextField(default="", blank=True, null=True)
    note = models.TextField(default="", blank=True, null=True)
    period = models.CharField(max_length=50)
    
    def __str__(self):
        return self.title

    # دالة للحصول على URL الصورة
    def get_image_url(self, image_field):
        if image_field:
            if hasattr(image_field, 'url'):
                return image_field.url
            else:
                return str(image_field)
        return None

    # دالة للحصول على URL الفيديو
    def get_video_url(self):
        if self.video:
            if hasattr(self.video, 'url'):
                return self.video.url
            else:
                return str(self.video)
        return None

class ServiceCard(models.Model):
    servicebooking = models.ForeignKey(ServiceBooking, on_delete=models.SET_NULL, null=True, blank=True )
    title = models.CharField(max_length=50)
    description = models.TextField()
    image = models.ImageField(upload_to="ServiceImages")
    def __str__(self):
        return self.title 



class Booking(models.Model):
    servicebooking = models.ForeignKey(ServiceBooking, on_delete=models.SET_NULL, null=True, blank=True )
    name = models.CharField(max_length=50)
    email = models.EmailField(max_length=254)
    phone = models.CharField(max_length=15)
    numofadult = models.IntegerField()
    date = models.CharField(max_length = 50)
    hotel = models.CharField(max_length=10, blank=True, null=True)
    room = models.CharField(max_length=10, blank=True, null=True)
    dropoff = models.CharField(max_length = 50,default="I don't need")
    policy = models.BooleanField(default= True)
    disease = models.CharField(max_length = 50,blank=True, null=True)
    def __str__(self):
        return f"{self.name}"


class TourRequest(models.Model):
    full_name = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    tour_date = models.DateField()
    num_people = models.PositiveIntegerField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.destination}"