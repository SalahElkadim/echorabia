from django.shortcuts import render, redirect
from .models import ServiceBooking, ServiceCard, Booking, TourRequest
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
import cloudinary.uploader
import os



def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')  # عدل على حسب الصفحة اللي تحب يرجع لها
        else:
            messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة')

    return render(request, 'tourapp/home.html')


def logout_view(request):
    logout(request)
    return redirect('home') 


def home(request):
    servicecards = ServiceCard.objects.all()
    return render(request, 'tourapp/home.html', {'servicecards' : servicecards})

def privacy(request):
    return render(request, 'tourapp/privacy.html')


@user_passes_test(lambda u: u.is_superuser)
def dashboard(request):
    servicecards = ServiceCard.objects.all()
    servicebooking = ServiceBooking.objects.all()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        try:
            if action == 'add_booking':
                # إنشاء الحجز أولاً
                booking = ServiceBooking.objects.create(
                    title=request.POST.get('title'),
                    description=request.POST.get('description'),
                    included=request.POST.get('included'),
                    exclusion=request.POST.get('exclusion'),
                    note=request.POST.get('note'),
                    period=request.POST.get('period')
                )
                
                # معالجة الملفات
                for field_name in ['image1', 'image2', 'image3']:
                    file = request.FILES.get(field_name)
                    if file:
                        if os.environ.get('RAILWAY_ENVIRONMENT'):
                            # رفع إلى Cloudinary
                            result = cloudinary.uploader.upload(
                                file,
                                folder='ServiceImages/',
                                transformation=[
                                    {'width': 1200, 'height': 800, 'crop': 'fill'},
                                    {'quality': 'auto'}
                                ]
                            )
                            # حفظ الـ public_id
                            setattr(booking, f'{field_name}_cloudinary', result['public_id'])
                        else:
                            # حفظ محلي
                            setattr(booking, field_name, file)
                
                # معالجة الفيديو
                video = request.FILES.get('video')
                if video:
                    if os.environ.get('RAILWAY_ENVIRONMENT'):
                        video_result = cloudinary.uploader.upload(
                            video,
                            resource_type='video',
                            folder='videos/'
                        )
                        booking.video_cloudinary = video_result['public_id']
                    else:
                        booking.video = video
                
                booking.save()
                messages.success(request, 'تم إضافة الحجز بنجاح!')
                
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
            
        return redirect('dashboard')
    
    return render(request, 'tourapp/dashboard.html', {
        'servicecards': servicecards, 
        'servicebooking': servicebooking
    })

def validate_file(file, file_type='image'):
    """
    التحقق من صحة الملف
    """
    if not file:
        return True, None
    
    # التحقق من الحجم
    max_size = 50 * 1024 * 1024  # 50MB للفيديو
    if file_type == 'image':
        max_size = 10 * 1024 * 1024  # 10MB للصور
    
    if file.size > max_size:
        return False, f'حجم الملف كبير جداً. الحد الأقصى {max_size/1024/1024}MB'
    
    # التحقق من نوع الملف
    if file_type == 'image':
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    else:
        allowed_types = ['video/mp4', 'video/avi', 'video/mov', 'video/wmv']
    
    if file.content_type not in allowed_types:
        return False, 'نوع الملف غير مدعوم'
    
    return True, None