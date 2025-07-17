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

