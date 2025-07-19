from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime
from cloudinary.models import CloudinaryField
import cloudinary.utils
import os



class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('owner', 'Owner'),
        ('customer', 'Customer')
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="customer")
    def __str__(self):
        return f"{self.username} ({self.role})"


from django.db import models
import os

class ServiceBooking(models.Model):
    # الحقول النصية
    title = models.CharField(max_length=50)
    description = models.TextField()
    included = models.TextField(default="", blank=True, null=True)
    exclusion = models.TextField(default="", blank=True, null=True)
    note = models.TextField(default="", blank=True, null=True)
    period = models.CharField(max_length=50)
    
    # الصور والفيديوهات - استخدم ImageField/FileField عادي
    image1 = models.ImageField(upload_to='ServiceImages/', blank=True, null=True)
    image2 = models.ImageField(upload_to='ServiceImages/', blank=True, null=True)
    image3 = models.ImageField(upload_to='ServiceImages/', blank=True, null=True)
    video = models.FileField(upload_to='videos/', blank=True, null=True)
    
    # حقول إضافية لحفظ Cloudinary public_ids (للإنتاج)
    image1_cloudinary = models.CharField(max_length=200, blank=True, null=True)
    image2_cloudinary = models.CharField(max_length=200, blank=True, null=True)
    image3_cloudinary = models.CharField(max_length=200, blank=True, null=True)
    video_cloudinary = models.CharField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return self.title
    
    # دوال مساعدة للحصول على الروابط
    def get_image1_url(self):
        if os.environ.get('RAILWAY_ENVIRONMENT') and self.image1_cloudinary:
            from cloudinary.utils import cloudinary_url
            url, options = cloudinary_url(self.image1_cloudinary)
            return url
        elif self.image1:
            return self.image1.url
        return None
    
    def get_image2_url(self):
        if os.environ.get('RAILWAY_ENVIRONMENT') and self.image2_cloudinary:
            from cloudinary.utils import cloudinary_url
            url, options = cloudinary_url(self.image2_cloudinary)
            return url
        elif self.image2:
            return self.image2.url
        return None
    
    def get_image3_url(self):
        if os.environ.get('RAILWAY_ENVIRONMENT') and self.image3_cloudinary:
            from cloudinary.utils import cloudinary_url
            url, options = cloudinary_url(self.image3_cloudinary)
            return url
        elif self.image3:
            return self.image3.url
        return None
    
    def get_video_url(self):
        if os.environ.get('RAILWAY_ENVIRONMENT') and self.video_cloudinary:
            from cloudinary.utils import cloudinary_url
            url, options = cloudinary_url(self.video_cloudinary, resource_type='video')
            return url
        elif self.video:
            return self.video.url
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