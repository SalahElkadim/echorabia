// payment_checkout.js

// تأكد من إضافة هذا السكريبت بعد تحميل مكتبة Moyasar Checkout في HTML
<script src="https://checkout.moyasar.com/v1/checkout.js"></script>

document.addEventListener("DOMContentLoaded", function () {
  const payButton = document.getElementById("pay-now");

  if (!payButton) return;

  payButton.addEventListener("click", function () {
    // ID الحجز، ممكن تجيبها ديناميكي من صفحة الحجز
    const bookingId = payButton.dataset.bookingId; // مثال: <button id="pay-now" data-booking-id="14">

    // 1️⃣ طلب إنشاء الدفع من DRF API
    fetch("/api/payment/create/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ booking_id: bookingId }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.error) {
          console.error(
            "Failed to create payment:",
            data.details || data.error
          );
          alert("❌ Failed to create payment. Check console.");
          return;
        }

        // 2️⃣ فتح Moyasar Checkout Popup
        Moyasar.open({
          checkoutUrl: data.payment_url, // استخدم checkout_url اللي رجعه السيرفر
          onClose: function () {
            console.log("Checkout closed without completing payment.");
          },
          onSuccess: function (payment) {
            console.log("Payment succeeded!", payment);
            alert("✅ Payment successful! Your booking is confirmed.");
            // ممكن هنا تعمل إعادة تحميل الصفحة أو تحديث UI
            location.reload();
          },
          onError: function (err) {
            console.error("Payment failed:", err);
            alert("❌ Payment failed. Please try again.");
          },
        });
      })
      .catch((error) => {
        console.error("Network error:", error);
        alert("❌ Network error. Please try again.");
      });
  });
});
