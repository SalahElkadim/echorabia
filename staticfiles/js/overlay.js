document
  .getElementById("open-login-modal")
  .addEventListener("click", function (e) {
    e.preventDefault();
    document.getElementById("login-modal").classList.remove("hidden");
    document.getElementById("login-overlay").classList.remove("hidden");
  });

document
  .getElementById("close-login-modal")
  .addEventListener("click", function () {
    document.getElementById("login-modal").classList.add("hidden");
    document.getElementById("login-overlay").classList.add("hidden");
  });

// يغلق النافذة لو ضغط على الخلفية
document.getElementById("login-overlay").addEventListener("click", function () {
  document.getElementById("login-modal").classList.add("hidden");
  document.getElementById("login-overlay").classList.add("hidden");
});
