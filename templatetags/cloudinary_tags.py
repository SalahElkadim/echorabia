from django import template
from django.conf import settings
import os

register = template.Library()

@register.simple_tag
def cloudinary_url(field, **kwargs):
    """
    إنشاء رابط Cloudinary مع تحويلات
    """
    if not field:
        return ''
    
    if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('PRODUCTION'):
        from cloudinary.utils import cloudinary_url
        url, options = cloudinary_url(str(field), **kwargs)
        return url
    else:
        # للتطوير المحلي
        return field.url if hasattr(field, 'url') else str(field)