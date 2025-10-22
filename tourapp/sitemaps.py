from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import ServiceCard

class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        # الصفحات الثابتة زي الصفحة الرئيسية، سياسة الخصوصية، إلخ
        return ['home', 'privacy',]

    def location(self, item):
        return reverse(item)

class ServiceCardSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return ServiceCard.objects.all()

    def lastmod(self, obj):
        return obj.id  # لو عندك حقل updated_at استخدمه بدل كدا
