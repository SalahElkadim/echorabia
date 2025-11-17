from django.shortcuts import render, redirect
from .models import ServiceBooking, ServiceCard, Booking, TourRequest,Main_price_model,Price_model,BookingPrice
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
from .integration_services import get_tour_guide_license_details, get_tour_operator_license_details
from payment.models import Payment, Invoice


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
    # ✅ عرض الريفيوهات المعتمدة فقط
    reviews = Review.objects.filter(is_approved=True).order_by('-created_at')

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.is_approved = False  # ✅ الريفيو غير معتمد افتراضياً
            review.save()
            messages.success(request, 'تم إرسال التقييم بنجاح! سيتم مراجعته قريباً.')
            return redirect('home')
    else:
        form = ReviewForm()

    return render(
        request,
        'tourapp/home.html',
        {
            'servicecards': servicecards,
            'reviews': reviews,
            'form': form,
        }
    )


def privacy(request):
    return render(request, 'tourapp/privacy.html')


# ثم عدّل دالة dashboard لتصبح:
@user_passes_test(lambda u: u.is_superuser)
def dashboard(request):
    servicecards = ServiceCard.objects.all()
    servicebooking = ServiceBooking.objects.all()
    main_prices = Main_price_model.objects.all()
    prices = Price_model.objects.select_related('main_price_model').all()
    
    # إضافة الريفيوهات المعلقة والمعتمدة
    pending_reviews = Review.objects.filter(is_approved=False).order_by('-created_at')
    approved_reviews = Review.objects.filter(is_approved=True).order_by('-created_at')
    
    # ✅ إضافة بيانات الدفع والحجوزات
    payments = Payment.objects.select_related(
        'booking', 
        'booking__servicebooking',
        'invoice'
    ).order_by('-created_at')
    
    bookings = Booking.objects.select_related(
        'servicebooking',
        'price'
    ).order_by('-created_at')
    
    # إحصائيات سريعة
    total_payments = payments.filter(status='paid').count()
    total_revenue = sum([p.amount / 100 for p in payments.filter(status='paid')])
    pending_payments = payments.filter(status='pending_form').count()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        try:
            # إنشاء حجز خدمة
            if action == 'add_booking':
                main_price_id = request.POST.get('main_price_id')
                main_price = None
                
                if main_price_id:
                    try:
                        main_price = Main_price_model.objects.get(id=main_price_id)
                    except Main_price_model.DoesNotExist:
                        pass
                
                booking = ServiceBooking.objects.create(
                    title=request.POST.get('title'),
                    description=request.POST.get('description'),
                    included=request.POST.get('included'),
                    exclusion=request.POST.get('exclusion'),
                    note=request.POST.get('note'),
                    period=request.POST.get('period'),
                    main_price_model=main_price,
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

            # تعديل نموذج رئيسي للأسعار
            elif action == 'edit_main_price':
                main_price_id = request.POST.get('main_price_id')
                title = request.POST.get('title')
                main_price = Main_price_model.objects.get(id=main_price_id)
                main_price.title = title
                main_price.save()
                messages.success(request, 'تم تعديل نموذج الأسعار الرئيسي بنجاح!')

            # حذف نموذج رئيسي للأسعار
            elif action == 'delete_main_price':
                main_price_id = request.POST.get('main_price_id')
                main_price = Main_price_model.objects.get(id=main_price_id)
                main_price.delete()
                messages.success(request, 'تم حذف نموذج الأسعار الرئيسي بنجاح!')

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
            
            # تعديل السعر
            elif action == 'edit_price':
                price_id = request.POST.get('price_id')
                price = Price_model.objects.get(id=price_id)
                price.numper_o_p = request.POST.get('numper_o_p')
                price.total_g = request.POST.get('total_g')
                price.total_g_d = request.POST.get('total_g_d')
                price.total_g_b = request.POST.get('total_g_b')
                price.total_g_v = request.POST.get('total_g_v')
                price.total_g_d_b = request.POST.get('total_g_d_b')
                price.total_g_d_v = request.POST.get('total_g_d_v')
                price.save()
                messages.success(request, 'تم تعديل السعر بنجاح!')

            # حذف السعر
            elif action == 'delete_price':
                price_id = request.POST.get('price_id')
                Price_model.objects.get(id=price_id).delete()
                messages.success(request, 'تم حذف السعر بنجاح!')

        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
        
        return redirect('dashboard')
    
    return render(request, 'tourapp/dashboard.html', {
        'servicecards': servicecards,
        'servicebooking': servicebooking,
        'main_prices': main_prices,
        'prices': prices,
        'pending_reviews': pending_reviews,
        'approved_reviews': approved_reviews,
        # ✅ إضافة البيانات الجديدة
        'payments': payments,
        'bookings': bookings,
        'total_payments': total_payments,
        'total_revenue': total_revenue,
        'pending_payments': pending_payments,
    })

# ثالثاً: إضافة دوال الموافقة والرفض
@user_passes_test(lambda u: u.is_superuser)
def approve_review(request, review_id):
    """الموافقة على الريفيو"""
    review = get_object_or_404(Review, id=review_id)
    review.is_approved = True
    review.save()
    messages.success(request, f'تم الموافقة على تقييم {review.name}')
    return redirect('dashboard')


@user_passes_test(lambda u: u.is_superuser)
def reject_review(request, review_id):
    """رفض وحذف الريفيو"""
    review = get_object_or_404(Review, id=review_id)
    review_name = review.name
    review.delete()
    messages.success(request, f'تم رفض وحذف تقييم {review_name}')
    return redirect('dashboard')



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
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        numofadult = int(request.POST.get('numofadult', 1))
        booking_date = request.POST.get('date')  # ✅ غيّر من 'booking_date' لـ 'date'
        hotel = request.POST.get('hotel', '')
        room = request.POST.get('room', '')
        include_dinner = request.POST.get('include_dinner') in ['on', 'true', '1']
        bus_type = request.POST.get('bus_type', 'none')
        dropoff = request.POST.get('dropoff', "I don't need")
        disease = request.POST.get('disease', '')
        policy_checked = request.POST.get('policy') == 'on'

        # نجيب سعر الرحلة بناءً على العدد ونوع العشاء والباص
        price_instance = Price_model.objects.get(
            main_price_model=service.main_price_model,
            numper_o_p=numofadult
        )

        # تحديد السعر حسب الحالة
        if numofadult <= 6:
            total_price = price_instance.total_g_d if include_dinner else price_instance.total_g
        else:
            if bus_type == 'vip':
                total_price = price_instance.total_g_d_v if include_dinner else price_instance.total_g_v
            elif bus_type == 'normal':
                total_price = price_instance.total_g_d_b if include_dinner else price_instance.total_g_b
            else:
                return JsonResponse({'error': 'Bus type required for more than 6 people'}, status=400)

        # إنشاء الحجز
        booking = Booking.objects.create(
            servicebooking=service,
            name=name,
            email=email,
            phone=phone,
            numofadult=numofadult,
            date=booking_date,
            hotel=hotel,
            room=room,
            dropoff=dropoff,
            policy=policy_checked,
            disease=disease,
            include_dinner=include_dinner,
            bus_type=bus_type,
        )

        # إنشاء كائن السعر المنفصل
        BookingPrice.objects.create(
            booking=booking,
            total_price=total_price
        )

        return JsonResponse({
            "success": True,
            "booking_id": booking.id,
            "total_price": float(total_price)
        })

    except Price_model.DoesNotExist:
        return JsonResponse({'error': 'No price found for this group size'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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


def verify_tour_guide(request, id_no, license_no):
    data = get_tour_guide_license_details(id_no, license_no)
    if data.get("errorCode") == 0:
        return JsonResponse({"status": "verified", "details": data})
    else:
        return JsonResponse({"status": "error", "message": data.get("errorMessage")})

def verify_operator(request):
    company_id = "1000120087"
    license_no = "73101348"
    commercial_no = "1010478246"
    data = get_tour_operator_license_details(company_id, license_no, commercial_no)
    return JsonResponse(data)

from django.http import HttpResponse

def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Allow: /",
        "Sitemap: https://echorabia.com/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
