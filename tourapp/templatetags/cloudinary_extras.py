
from django import template
from django.conf import settings
import os

register = template.Library()

@register.simple_tag
def get_image_url(image_field, **kwargs):
    """
    الحصول على رابط الصورة سواء كانت محلية أو في Cloudinary
    """
    if not image_field:
        return ''
    
    # إذا كان في الإنتاج واستخدمنا Cloudinary
    if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('PRODUCTION'):
        try:
            from cloudinary.utils import cloudinary_url
            # إذا كان CloudinaryField
            if hasattr(image_field, 'public_id'):
                url, options = cloudinary_url(image_field.public_id, **kwargs)
                return url
            # إذا كان string (public_id محفوظ كنص)
            elif isinstance(image_field, str):
                url, options = cloudinary_url(image_field, **kwargs)
                return url
            # إذا كان ImageField عادي
            else:
                return image_field.url if hasattr(image_field, 'url') else str(image_field)
        except:
            # في حالة الخطأ، استخدم الرابط العادي
            return image_field.url if hasattr(image_field, 'url') else str(image_field)
    else:
        # للتطوير المحلي
        return image_field.url if hasattr(image_field, 'url') else str(image_field)

@register.simple_tag
def get_video_url(video_field):
    """
    الحصول على رابط الفيديو
    """
    if not video_field:
        return ''
    
    if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('PRODUCTION'):
        try:
            from cloudinary.utils import cloudinary_url
            if hasattr(video_field, 'public_id'):
                url, options = cloudinary_url(video_field.public_id, resource_type='video')
                return url
            elif isinstance(video_field, str):
                url, options = cloudinary_url(video_field, resource_type='video')
                return url
            else:
                return video_field.url if hasattr(video_field, 'url') else str(video_field)
        except:
            return video_field.url if hasattr(video_field, 'url') else str(video_field)
    else:
        return video_field.url if hasattr(video_field, 'url') else str(video_field)
