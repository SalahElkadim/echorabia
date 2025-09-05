from django.contrib import admin
from .models import CustomUser, ServiceBooking , ServiceCard ,Booking, TourRequest,Review

admin.site.register(CustomUser)
admin.site.register(ServiceBooking)
admin.site.register(ServiceCard)
admin.site.register(Booking)
admin.site.register(TourRequest)
admin.site.register(Review)


