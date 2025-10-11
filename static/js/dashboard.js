function openModal(modalId) {
  document.getElementById(modalId).style.display = "block";
  document.body.style.overflow = "hidden";
}

function closeModal(modalId) {
  document.getElementById(modalId).style.display = "none";
  document.body.style.overflow = "auto";
}

function showLoading() {
  const loadingElements = document.querySelectorAll(".loading");
  loadingElements.forEach((el) => (el.style.display = "block"));
}

// Close modal when clicking outside
window.onclick = function (event) {
  const modals = document.querySelectorAll(".modal");
  modals.forEach((modal) => {
    if (event.target === modal) {
      modal.style.display = "none";
      document.body.style.overflow = "auto";
    }
  });
};

// File upload preview
document.querySelectorAll('input[type="file"]').forEach((input) => {
  input.addEventListener("change", function (e) {
    const file = e.target.files[0];
    const label = e.target.nextElementSibling;
    if (file) {
      label.innerHTML = `<i class="fas fa-check"></i> تم اختيار: ${file.name}`;
      label.style.background = "#e8f5e8";
      label.style.borderColor = "#4caf50";
    }
  });
});

// Animate statistics on load
window.addEventListener("load", function () {
  const statNumbers = document.querySelectorAll(".stat-card h3");
  statNumbers.forEach((stat) => {
    const finalValue = parseInt(stat.textContent);
    if (!isNaN(finalValue)) {
      let current = 0;
      const increment = finalValue / 50;
      const timer = setInterval(() => {
        current += increment;
        if (current >= finalValue) {
          stat.textContent = finalValue;
          clearInterval(timer);
        } else {
          stat.textContent = Math.floor(current);
        }
      }, 30);
    }
  });
});

// Add some interactive effects
document.addEventListener("DOMContentLoaded", function () {
  // Smooth scrolling
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute("href"));
      if (target) {
        target.scrollIntoView({
          behavior: "smooth",
        });
      }
    });
  });

  // Add ripple effect to buttons
  document.querySelectorAll(".action-btn, .submit-btn").forEach((button) => {
    button.addEventListener("click", function (e) {
      const ripple = document.createElement("span");
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;

      ripple.style.cssText = `
                        position: absolute;
                        border-radius: 50%;
                        background: rgba(255,255,255,0.3);
                        transform: scale(0);
                        animation: ripple 0.6s linear;
                        width: ${size}px;
                        height: ${size}px;
                        left: ${x}px;
                        top: ${y}px;
                    `;

      this.appendChild(ripple);
      setTimeout(() => ripple.remove(), 600);
    });
  });
});


// ==================== فتح وإغلاق النوافذ المنبثقة ====================
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

// إغلاق المودال عند الضغط خارجه
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

// ==================== إظهار شاشة التحميل ====================
function showLoading() {
    const loadingElements = document.querySelectorAll('.loading');
    loadingElements.forEach(loading => {
        loading.style.display = 'block';
    });
}

// ==================== معاينة الصور قبل الرفع ====================
document.querySelectorAll('input[type="file"]').forEach(input => {
    input.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const label = this.nextElementSibling;
            if (label && label.classList.contains('file-upload-label')) {
                const span = label.querySelector('span');
                if (span) {
                    span.textContent = file.name;
                }
            }
        }
    });
});

// ==================== وظيفة إظهار وإخفاء قوائم الأسعار ====================
document.addEventListener('DOMContentLoaded', function() {
    // الحصول على جميع العناوين الرئيسية
    const mainTitles = document.querySelectorAll('.main-title');
    
    mainTitles.forEach(title => {
        // إضافة حدث الضغط
        title.addEventListener('click', function() {
            // الحصول على القائمة الفرعية التابعة لهذا العنوان
            const priceList = this.nextElementSibling;
            
            // تبديل الكلاس active للسهم
            this.classList.toggle('active');
            
            // إظهار أو إخفاء القائمة
            if (priceList && priceList.classList.contains('price-list')) {
                priceList.classList.toggle('show');
            }
        });
        
        // إضافة تأثير hover
        title.addEventListener('mouseenter', function() {
            this.style.background = 'rgba(59, 130, 246, 0.1)';
        });
        
        title.addEventListener('mouseleave', function() {
            if (!this.classList.contains('active')) {
                this.style.background = 'transparent';
            }
        });
    });
});

// ==================== وظيفة فتح مودال التعديل ====================
function openEditModal(id, numper, g, gd, gb, gv, gdb, gdv) {
    document.getElementById('price_id').value = id;
    document.getElementById('numper_o_p').value = numper;
    document.getElementById('total_g').value = g;
    document.getElementById('total_g_d').value = gd;
    document.getElementById('total_g_b').value = gb;
    document.getElementById('total_g_v').value = gv;
    document.getElementById('total_g_d_b').value = gdb;
    document.getElementById('total_g_d_v').value = gdv;
    openModal('edit-price-modal');
}

// ==================== التحقق من النماذج قبل الإرسال ====================
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function(e) {
        const requiredFields = this.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                field.style.borderColor = '#ef4444';
                
                // إزالة اللون الأحمر بعد الكتابة
                field.addEventListener('input', function() {
                    this.style.borderColor = '';
                }, { once: true });
            }
        });
        
        if (!isValid) {
            e.preventDefault();
            alert('يرجى ملء جميع الحقول المطلوبة');
        }
    });
});

// ==================== تأثيرات إضافية ====================
// إضافة تأثير عند التمرير على البطاقات
document.querySelectorAll('.service-card, .stat-card').forEach(card => {
    card.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-8px)';
    });
    
    card.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
    });
});

// ==================== رسالة تأكيد قبل الحذف ====================
document.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
        if (!confirm('هل أنت متأكد من الحذف؟')) {
            e.preventDefault();
            e.stopPropagation();
        }
    });
});

// ==================== تحديث عداد الخدمات ====================
function updateServicesCount() {
    const servicesCount = document.querySelectorAll('.service-card').length;
    const totalServicesElement = document.getElementById('total-services');
    if (totalServicesElement) {
        totalServicesElement.textContent = servicesCount;
    }
}

// تحديث العداد عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', updateServicesCount);