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

 