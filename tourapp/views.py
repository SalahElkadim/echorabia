from django.shortcuts import render, redirect
from .models import ServiceBooking, ServiceCard, Booking, TourRequest,Payment
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
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        try:
            # إنشاء حجز خدمة
            if action == 'add_booking':
                # مع CloudinaryField، Django بيتعامل مع رفع الصور تلقائياً
                booking = ServiceBooking.objects.create(
                    title=request.POST.get('title'),
                    description=request.POST.get('description'),
                    included=request.POST.get('included'),
                    exclusion=request.POST.get('exclusion'),
                    note=request.POST.get('note'),
                    period=request.POST.get('period'),
                    image1=request.FILES.get('image1'),  # CloudinaryField بيرفع الصورة تلقائياً
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
                
                # إنشاء الكرت - CloudinaryField بيتعامل مع الصورة تلقائياً
                card = ServiceCard(
                    title=card_title,
                    description=card_description,
                    image=card_image  # مباشرة من الـ request.FILES
                )
                
                # ربط الكرت بالحجز إذا كان موجود
                if booking_id:
                    try:
                        booking = ServiceBooking.objects.get(id=booking_id)
                        card.servicebooking = booking
                    except ServiceBooking.DoesNotExist:
                        pass
                
                card.save()
                messages.success(request, 'تم إضافة كرت الخدمة بنجاح!')
        
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

        # 1️⃣ إنشاء الحجز مبدئيًا (pending)
        booking = Booking.objects.create(
            servicebooking=service,
            name=request.POST.get('name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            numofadult=int(request.POST.get('adults')),
            date=request.POST.get('booking_date'),
            hotel=request.POST.get('hotel', ''),
            room=request.POST.get('room_number', ''),
            dropoff=request.POST.get('dropoff', "I don't need"),
            policy=request.POST.get('cancellation_policy') == 'on',
            disease=request.POST.get('disease'),
        )

        # 2️⃣ إنشاء طلب دفع عبر ميسر (Checkout Page)
        url = "https://api.moyasar.com/v1/payments"
        data = {
            "amount": int(service.cost * 100),  # بالهللة
            "currency": "SAR",
            "description": f"Booking for {service.title}",
            "callback_url": request.build_absolute_uri("/payments/callback/"),
            # 🔥 للبطاقة الحقيقية - احذف الـ source من هنا
             "source": {
                 "type": "creditcard",
                 "name": "Test Card",
                 "number": "4111111111111111",
                 "month": "12",
                 "year": "25",
                 "cvc": "123"
             }
        }

        response = requests.post(
            url,
            auth=(settings.MOYASAR_SECRET_KEY, ""),
            json=data,
        )

        if response.status_code != 200:
            return JsonResponse({
                'error': 'Payment creation failed', 
                'details': response.json()
            }, status=400)

        payment_data = response.json()

        # 3️⃣ حفظ الدفع
        payment = Payment.objects.create(
            booking=booking,
            moyasar_id=payment_data.get("id"),
            amount=service.cost,
            status=payment_data.get("status", "failed")
        )

        # 4️⃣ إرجاع الـ payment URL بدلاً من redirect
        transaction_url = payment_data.get("source", {}).get("transaction_url")
        
        if transaction_url:
            return JsonResponse({
                'success': True,
                'transaction_url': transaction_url,
                'payment_id': payment_data.get("id")
            })
        else:
            return JsonResponse({
                'error': 'No checkout URL returned', 
                'details': payment_data
            }, status=400)

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

        messages.success(request, "Thanks, we'll contact you soon!")
        return redirect('home')  # أو redirect('create_tour') لو عندك صفحة تأكيد

    return render(request, 'tourapp/home.html')

import hmac
import hashlib
from django.conf import settings
def verify_signature(request):
    signature = request.headers.get("Moyasar-Signature")
    if not signature:
        return False

    # البودي اللي بعتته ميسر زي ما هو (RAW)
    body = request.body.decode("utf-8")

    # حساب HMAC باستخدام secret token بتاع الويبهوك
    expected_signature = hmac.new(
        key=settings.MOYASAR_WEBHOOK_SECRET.encode("utf-8"),
        msg=body.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


@csrf_exempt
def payment_callback(request):
    # ✅ تحقق من التوقيع
    if not verify_signature(request):
        return JsonResponse({"error": "Invalid signature"}, status=400)

    data = request.POST or request.GET or {}
    moyasar_id = data.get("id")
    status = data.get("status")

    try:
        payment = Payment.objects.get(moyasar_id=moyasar_id)
        booking = payment.booking
        service = booking.servicebooking

        # ✅ تحديث حالة الدفع
        payment.status = status
        payment.save()

        # ✅ لو عايز تحدث البوكينج كمان
        if status == "paid":
            booking.confirmed = True  # لو عندك في النموذج
            booking.save()

        # ✅ إرسال إيميل
        subject = f'New Booking: {service.title}'
        message = f'''
        A new booking has been made:

        Service: {service.title}
        Name: {booking.name}
        Email: {booking.email}
        Phone: {booking.phone}
        Number of Adults: {booking.numofadult}
        Booking Date: {booking.date}
        Hotel: {booking.hotel}
        Room Number: {booking.room}
        Drop-off: {booking.dropoff}
        Medical Conditions: {booking.disease}
        Agreed to Cancellation Policy: {'Yes' if booking.policy else 'No'}
        '''

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            ['echorabia@gmail.com'],
            fail_silently=False,
        )
    except Payment.DoesNotExist:
        return JsonResponse({"error": "Payment not found"}, status=404)

    return JsonResponse({"message": "تم التحديث"})

