from django.shortcuts import render, redirect
from .models import ServiceBooking, ServiceCard, Booking, TourRequest,Main_price_model,Price_model
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from .models import Review
from .forms import ReviewForm
import requests
from django.conf import settings
import logging

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
    reviews = Review.objects.order_by('-created_at')  # كل الريفيوز

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')  # إعادة تحميل الصفحة
    else:
        form = ReviewForm()

    return render(
        request,
        'tourapp/home.html',
        {
            'servicecards': servicecards,
            'reviews': reviews,
            'form': form,   # ✅ لازم تبعتها هنا
        }
    )


def privacy(request):
    return render(request, 'tourapp/privacy.html')

@user_passes_test(lambda u: u.is_superuser)
def dashboard(request):
    servicecards = ServiceCard.objects.all()
    servicebooking = ServiceBooking.objects.all()
    main_prices = Main_price_model.objects.all()
    prices = Price_model.objects.select_related('main_price_model').all()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        try:
            # إنشاء حجز خدمة
            if action == 'add_booking':
                booking = ServiceBooking.objects.create(
                    title=request.POST.get('title'),
                    description=request.POST.get('description'),
                    included=request.POST.get('included'),
                    exclusion=request.POST.get('exclusion'),
                    note=request.POST.get('note'),
                    period=request.POST.get('period'),
                    image1=request.FILES.get('image1'),
                    image2=request.FILES.get('image2'),
                    image3=request.FILES.get('image3'),
                )
                messages.success(request, 'تم إضافة الحجز بنجاح!')
            
            # إنشاء كرت خدمة
            elif action == 'add_card':
                card_title = request.POST.get('card_title')
                card_description = request.POST.get('card_description')
                card_image = request.FILES.get('card_image')
                booking_id = request.POST.get('card_id')
                
                card = ServiceCard(
                    title=card_title,
                    description=card_description,
                    image=card_image
                )
                
                if booking_id:
                    try:
                        booking = ServiceBooking.objects.get(id=booking_id)
                        card.servicebooking = booking
                    except ServiceBooking.DoesNotExist:
                        pass
                
                card.save()
                messages.success(request, 'تم إضافة كرت الخدمة بنجاح!')

            # إضافة نموذج رئيسي للأسعار
            elif action == 'add_main_price':
                title = request.POST.get('title')
                Main_price_model.objects.create(title=title)
                messages.success(request, 'تم إضافة نموذج الأسعار الرئيسي بنجاح!')

            # إضافة سعر فرعي مرتبط بنموذج رئيسي
            elif action == 'add_price':
                main_id = request.POST.get('main_price_id')
                main_model = Main_price_model.objects.get(id=main_id)

                Price_model.objects.create(
                    main_price_model=main_model,
                    numper_o_p=request.POST.get('numper_o_p') or None,
                    total_g=request.POST.get('total_g') or None,
                    total_g_d=request.POST.get('total_g_d') or None,
                    total_g_b=request.POST.get('total_g_b') or None,
                    total_g_v=request.POST.get('total_g_v') or None,
                    total_g_d_b=request.POST.get('total_g_d_b') or None,
                    total_g_d_v=request.POST.get('total_g_d_v') or None,
                )
                messages.success(request, 'تم إضافة الأسعار الفرعية بنجاح!')

        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
        
        return redirect('dashboard')
    
    return render(request, 'tourapp/dashboard.html', {
        'servicecards': servicecards,
        'servicebooking': servicebooking,
        'main_prices': main_prices,
        'prices': prices,
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
        'moyasar_key': settings.MOYASAR_PUBLISHABLE_KEY

    }
    
    return render(request, 'tourapp/service_detail.html', context)

logger = logging.getLogger(__name__)
@csrf_exempt
def book_service(request, service_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    service = get_object_or_404(ServiceBooking, id=service_id)

    try:
        booking = Booking.objects.create(
            servicebooking=service,
            name=request.POST.get('name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            numofadult=int(request.POST.get('adults', 1)),
            date=request.POST.get('booking_date'),
            hotel=request.POST.get('hotel', ''),
            room=request.POST.get('room', ''),
            dropoff=request.POST.get('dropoff', "I don't need"),
            policy=request.POST.get('cancellation_policy') == 'on',
            disease=request.POST.get('disease', ''),
        )
        return JsonResponse({
            "success": True,
            "booking_id": booking.id
        })
    except Exception as e:
        logger.error(f"Booking creation failed: {e}")
        return JsonResponse({'error': 'Booking creation failed', 'details': str(e)}, status=400)

#طلب انشاء رحلة مخصصة 
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

        messages.success(request, "Thanks, we'll contact you soon!")
        return redirect('home')  

    return render(request, 'tourapp/home.html')

