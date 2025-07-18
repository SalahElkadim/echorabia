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

@user_passes_test(lambda u: u.is_superuser)
def delete_item(request):
    if request.method == "POST":
        card_id = request.POST.get("item_id")
        card = get_object_or_404(ServiceCard, id=card_id)
        card.delete()
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error", "message": "Invalid request"})



def service_detail(request, service_id):
    service_card = get_object_or_404(ServiceCard, id=service_id)  
    service_booking = service_card.servicebooking
    context = {
        'service_card': service_card,
        'service_booking': service_booking, 
    }
    
    return render(request, 'tourapp/service_detail.html', context)


def book_service(request, service_id):
    if request.method == 'POST':
        service = get_object_or_404(ServiceBooking, id=service_id)

        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        numofadult = int(request.POST.get('adults'))
        date = request.POST.get('booking_date')
        hotel = request.POST.get('hotel', '')
        room = request.POST.get('room_number', '')
        dropoff = request.POST.get('dropoff', 'I don’t need')
        policy = request.POST.get('cancellation_policy') == 'on'
        disease = request.POST.get('disease')

        booking = Booking.objects.create(
            servicebooking=service,
            name=name,
            email=email,
            phone=phone,
            numofadult=numofadult,
            date=date,
            hotel=hotel,
            room=room,
            dropoff=dropoff,
            policy=policy,
            disease=disease
        )

        # إرسال الإيميل لصاحب الموقع
        subject = f'New Booking: {service.title}'
        message = f'''
        A new booking has been made:

        Service: {service.title}
        Name: {name}
        Email: {email}
        Phone: {phone}
        Number of Adults: {numofadult}
        Booking Date: {date}
        Hotel: {hotel}
        Room Number: {room}
        Drop-off: {dropoff}
        Medical Conditions: {disease}
        Agreed to Cancellation Policy: {'Yes' if policy else 'No'}
        '''

        admin_email = 'echorabia@gmail.com'  # استبدلها ببريد صاحب الموقع

        send_mail(
            subject,
            message,
            None,               # from email, يستخدم DEFAULT_FROM_EMAIL
            [admin_email],
            fail_silently=False,
        )

        return JsonResponse({'message': 'Booking successful'})

    return JsonResponse({'error': 'Invalid request'}, status=400)

def create_tour_request(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        destination = request.POST.get('destination')
        tour_date = request.POST.get('tour_date')
        num_people = request.POST.get('num_people')
        phone = request.POST.get('phone')
        email = request.POST.get('email')

        # حفظ الطلب
        TourRequest.objects.create(
            full_name=full_name,
            destination=destination,
            tour_date=tour_date,
            num_people=num_people,
            phone=phone,
            email=email
        )

        messages.success(request, 'Your tour request has been submitted successfully!')
        return redirect('home')  # أو redirect('create_tour') لو عندك صفحة تأكيد

    return render(request, 'tourapp/home.html')

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