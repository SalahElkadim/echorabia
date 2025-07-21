
from django.urls import path
from . import views
from django.views.generic import TemplateView
from django.contrib.sitemaps.views import sitemap
from .sitemaps import ServiceCardSitemap

sitemaps = {'services': ServiceCardSitemap}


urlpatterns = [
    path('', views.home, name= 'home'),
    path('privacy/', views.privacy, name='privacy'),
    path('dashboard', views.dashboard, name= 'dashboard'),
    path("delete-item/", views.delete_item, name="delete_item"),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('service/<int:service_id>/', views.service_detail, name='service_detail'),
    path('book-service/<int:service_id>/', views.book_service, name='book_service'),
    path('create-tour/', views.create_tour_request, name='create_tour'),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap')


    
]
# urls.py

