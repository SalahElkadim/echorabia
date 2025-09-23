  const accordions = document.querySelectorAll('.accordion');
  accordions.forEach(btn => {
    btn.addEventListener('click', () => {
      btn.classList.toggle('active');
      const panel = btn.nextElementSibling;
      if (panel.style.maxHeight) {
        panel.style.maxHeight = null;
      } else {
        panel.style.maxHeight = panel.scrollHeight + "px";
      }
    });
  });

  // Modal logic
  const modal = document.getElementById('bookingModal');
  const openBtn = document.querySelector('.book-btn');
  const closeBtn = document.querySelector('.close-btn');

  openBtn.addEventListener('click', () => {
    modal.style.display = 'flex';
  });

  closeBtn.addEventListener('click', () => {
    modal.style.display = 'none';
  });

  window.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.style.display = 'none';
    }
  });


  const adultsInput = document.querySelector('input[name="adults"]');
  const totalPriceEl = document.getElementById("totalPrice");
  const basePrice = parseFloat(totalPriceEl.dataset.basePrice);

  adultsInput.addEventListener("input", () => {
    const numAdults = parseInt(adultsInput.value) || 0;
    const total = basePrice * numAdults;
    totalPriceEl.textContent = total.toLocaleString(); // لإظهارها بصيغة مفهومة
  });

// إرسال نموذج الحجز عبر Fetch API
document.getElementById("bookingForm").addEventListener("submit", function(e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);

    // إضافة loading state
    const submitButton = form.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.textContent = 'Processing...';
    submitButton.disabled = true;

    fetch(`/book_service/${service_id}/`, {  // تأكد إن service_id متوفر
        method: "POST",
        headers: {
            'X-CSRFToken': document.querySelector("[name=csrfmiddlewaretoken]").value
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.checkout_url) {
            // 🔥 فتح صفحة الدفع في نفس التاب
            window.location.href = data.checkout_url;
            
            // 🔥 أو فتحها في تاب جديد (اختياري)
            // window.open(data.checkout_url, '_blank');
        } else {
            alert("❌ An error occurred while processing payment: " + (data.error || 'Unknown error'));
            console.error('Payment error:', data);
        }
    })
    .catch(error => {
        alert("❌ Network error. Please try again.");
        console.error('Network error:', error);
    })
    .finally(() => {
        // إعادة الزر لحالته الأصلية
        submitButton.textContent = originalText;
        submitButton.disabled = false;
    });
});