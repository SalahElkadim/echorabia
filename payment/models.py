from django.db import models
from django.utils import timezone


class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('canceled', 'Canceled'),
    ]
    
    moyasar_id = models.CharField(max_length=255, null=True, blank=True)
    amount = models.IntegerField()  # المبلغ بالهللة
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="initiated")
    currency = models.CharField(max_length=10, default="SAR")
    description = models.TextField(blank=True, null=True)
    
    # تواريخ مهمة
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    
    # معلومات إضافية من Moyasar
    moyasar_fee = models.IntegerField(blank=True, null=True)  # رسوم ميسر
    source_type = models.CharField(max_length=50, blank=True, null=True)  # نوع مصدر الدفع

    def __str__(self):
        return f"Payment {self.moyasar_id} - {self.status}"

    @property
    def amount_in_sar(self):
        """المبلغ بالريال السعودي"""
        return self.amount / 100

    def mark_as_paid(self):
        """تحديد الدفعة كمدفوعة"""
        if self.status != 'paid':
            self.status = 'paid'
            self.paid_at = timezone.now()
            self.save()


class Invoice(models.Model):
    INVOICE_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('canceled', 'Canceled'),
        ('refunded', 'Refunded'),
    ]
    
    payment = models.OneToOneField(
        'Payment',
        on_delete=models.CASCADE,
        related_name='invoice'
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # المبلغ بالريال
    currency = models.CharField(max_length=10, default='SAR')
    description = models.TextField(blank=True, null=True)
    
    # معلومات العميل (نسخة من بيانات المستخدم وقت إنشاء الفاتورة)
    customer_name = models.CharField(max_length=200, blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # التواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    due_date = models.DateTimeField(blank=True, null=True)
    
    # الحالة
    status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default='pending')
    
    # معلومات إضافية
    notes = models.TextField(blank=True, null=True)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # ضريبة القيمة المضافة
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['payment']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.payment.moyasar_id}"

    @property
    def total_amount(self):
        """إجمالي المبلغ مع الضريبة"""
        return self.amount + self.tax_amount

    @property
    def is_paid(self):
        """التحقق من كون الفاتورة مدفوعة"""
        return self.status == 'paid' and self.paid_at is not None

    def mark_as_paid(self):
        """تحديد الفاتورة كمدفوعة"""
        if not self.is_paid:
            self.status = 'paid'
            self.paid_at = timezone.now()
            self.save()

    