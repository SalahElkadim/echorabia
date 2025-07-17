from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime



class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('owner', 'Owner'),
        ('customer', 'Customer')
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="customer")
    def __str__(self):
        return f"{self.username} ({self.role})"


class ServiceBooking(models.Model):
    image1 = models.ImageField(upload_to='ServiceImages/', blank=True, null=True)
    image2 = models.ImageField(upload_to='ServiceImages/', blank=True, null=True)
    image3 = models.ImageField(upload_to='ServiceImages/', blank=True, null=True)
    video = models.FileField(upload_to='videos/', blank=True, null=True)
    title = models.CharField(max_length=50)
    description = models.TextField()
    included = models.TextField(default = "",blank=True, null=True)
    exclusion = models.TextField(default = "", blank=True, null=True)
    note = models.TextField(default = "", blank=True, null=True)
    period = models.CharField(max_length=50)

    def __str__(self):
        return self.title 

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
    date = models.CharField()
    hotel = models.CharField(max_length=10, blank=True, null=True)
    room = models.CharField(max_length=10, blank=True, null=True)
    dropoff = models.CharField(default="I don't need")
    policy = models.BooleanField(default= True)
    disease = models.CharField(blank=True, null=True)
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