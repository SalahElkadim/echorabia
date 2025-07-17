// إغلاق النافذة بعد الحجز
document.getElementById("bookingForm").addEventListener("submit", function (e) {
  e.preventDefault();

  const form = e.target;
  const formData = new FormData(form);
  const totalPrice = parseFloat(
    document.getElementById("totalPrice").textContent
  );
  formData.append("totalprice", totalPrice);

  fetch(form.getAttribute("action") || window.location.href, {
    method: "POST",
    headers: {
      "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
    },
    body: formData,
  })
    .then((response) => {
      if (response.ok) {
        document.getElementById("successOverlay").style.display = "flex";
        form.style.display = "none";
        document.getElementById("totalPrice").textContent = totalPrice;
      } else {
        alert("❌ An error occurred while booking. Please try again.");
      }
    })
    .catch((error) => {
      alert("❌ Network error. Please try again.");
      console.error(error);
    });
});

document.getElementById("bookingModal").style.display = "none";

// Toggle mobile menu
function toggleMenu() {
  const navLinks = document.querySelector(".nav-links");
  navLinks.classList.toggle("active");
}

// Smooth scroll
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute("href"));
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
});

// Observer animation
const observerOptions = {
  threshold: 0.1,
  rootMargin: "0px 0px -50px 0px",
};
const observer = new IntersectionObserver(function (entries) {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.style.animation = "fadeInUp 0.6s ease-out forwards";
    }
  });
}, observerOptions);

document.querySelectorAll(".service-card").forEach((card) => {
  observer.observe(card);
});

// intlTelInput إعداد
const phoneInputField = document.querySelector("#phone");
const iti = window.intlTelInput(phoneInputField, {
  initialCountry: "sa",
  preferredCountries: ["sa", "eg", "ae", "kw", "qa"],
  utilsScript:
    "https://cdn.jsdelivr.net/npm/intl-tel-input@17/build/js/utils.js",
});
document.querySelector("form").addEventListener("submit", function (e) {
  const fullPhoneNumber = iti.getNumber();
  phoneInputField.value = fullPhoneNumber;
});

// Flatpickr
flatpickr("#tour_date", {
  dateFormat: "Y-m-d",
  locale: "en",
});

// Cancellation policy
function formatDate(date) {
  const options = { day: "2-digit", month: "long", year: "numeric" };
  return date.toLocaleDateString("en-US", options);
}
document.addEventListener("DOMContentLoaded", function () {
  const now = new Date();
  const cancelDeadline = new Date(now);
  cancelDeadline.setDate(cancelDeadline.getDate() + 3);
  cancelDeadline.setHours(0, 0, 0, 0);
  const formattedDate = formatDate(cancelDeadline);

  const policyText = `
    Cancellation policy
    <hr>
    Fully refundable until ${formattedDate} at 00:00
    <hr>
    Non-refundable after ${formattedDate} at 00:00
  `;
  document.getElementById("cancellationPolicyText").innerHTML = policyText;
});
