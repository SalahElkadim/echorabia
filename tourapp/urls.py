
from django.urls import path
from . import views
from django.contrib import sitemaps
from django.contrib.sitemaps.views import sitemap
from tourapp.sitemaps import StaticViewSitemap, ServiceCardSitemap

sitemaps_dict = {
    'static': StaticViewSitemap,
    'services': ServiceCardSitemap,
}
urlpatterns = [
    path('', views.home, name= 'home'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
    path('dashboard', views.dashboard, name= 'dashboard'),
    path("delete-item/", views.delete_item, name="delete_item"),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('service/<int:service_id>/', views.service_detail, name='service_detail'),
    path('book-service/<int:service_id>/', views.book_service, name='book_service'),
    path('create-tour/', views.create_tour_request, name='create_tour'),
    path('approve-review/<int:review_id>/', views.approve_review, name='approve_review'),
    path('reject-review/<int:review_id>/', views.reject_review, name='reject_review'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps_dict}, name='django.contrib.sitemaps.views.sitemap'),
    path("robots.txt", views.robots_txt, name="robots_txt"),
    path('verify/guide/<str:id_no>/<str:license_no>/', views.verify_tour_guide, name='verify_tour_guide'),
    path('verify/operator/', views.verify_operator, name='verify_operator'),



    




    
]
# urls.py
