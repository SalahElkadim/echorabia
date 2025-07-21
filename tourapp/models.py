from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime
from cloudinary.models import CloudinaryField


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('owner', 'Owner'),
        ('customer', 'Customer')
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="customer")
    def __str__(self):
        return f"{self.username} ({self.role})"

class ServiceBooking(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    included = models.TextField(blank=True, null=True)
    exclusion = models.TextField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    period = models.CharField(max_length=100, blank=True, null=True)

    image1 = CloudinaryField('image1', blank=True, null=True)
    image2 = CloudinaryField('image2', blank=True, null=True)
    image3 = CloudinaryField('image3', blank=True, null=True)

    def __str__(self):
        return self.title


class ServiceCard(models.Model):
    servicebooking = models.ForeignKey(ServiceBooking, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=50)
    description = models.TextField()
    image = CloudinaryField('image', blank=True, null=True)

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