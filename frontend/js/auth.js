// frontend/js/auth.js
// ============================================
// AIRA - AUTHENTICATION LOGIC
// ============================================

// ============================================
// UTILITY FUNCTIONS
// ============================================

function showError(message) {
  const errorEl = document.getElementById("errorMessage");
  if (errorEl) {
    errorEl.className = "error-message show";
    errorEl.textContent = message;
  }
}

function showSuccess(message) {
  const errorEl = document.getElementById("errorMessage");
  if (errorEl) {
    errorEl.className = "success-message show";
    errorEl.textContent = message;
  }
}

function hideError() {
  const errorEl = document.getElementById("errorMessage");
  if (errorEl) {
    errorEl.classList.remove("show");
  }
}

function setLoading(buttonId, isLoading) {
  const btn = document.getElementById(buttonId);
  if (!btn) return;

  const textSpan = btn.querySelector(".btn-text");
  const loadingSpan = btn.querySelector(".btn-loading");

  if (isLoading) {
    btn.disabled = true;
    if (textSpan) textSpan.style.display = "none";
    if (loadingSpan) loadingSpan.style.display = "inline-flex";
  } else {
    btn.disabled = false;
    if (textSpan) textSpan.style.display = "inline";
    if (loadingSpan) loadingSpan.style.display = "none";
  }
}

// ============================================
// LOGIN FORM
// ============================================

const loginForm = document.getElementById("loginForm");
if (loginForm) {
  // Cek apakah user sudah login
  fetch("/api/auth/me", {
    credentials: "same-origin",
  })
    .then((res) => {
      if (res.ok) {
        window.location.href = "/";
      }
    })
    .catch(() => {});

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideError();

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const rememberMe = document.getElementById("rememberMe")?.checked || false;

    // Validasi
    if (!email || !password) {
      showError("Please enter both email and password");
      return;
    }

    // Validasi email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      showError("Please enter a valid email address");
      return;
    }

    setLoading("loginBtn", true);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "same-origin",
        body: JSON.stringify({
          email,
          password,
          remember: rememberMe,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        showError(data.error || "Login failed. Please try again.");
        setLoading("loginBtn", false);
        return;
      }

      // Simpan user info
      localStorage.setItem("aira_user", JSON.stringify(data.user));

      // Tampilkan sukses
      showSuccess("Login successful! Redirecting...");

      // Redirect ke halaman utama
      setTimeout(() => {
        window.location.href = "/";
      }, 500);
    } catch (error) {
      console.error("Login error:", error);
      showError("Network error. Please check your connection.");
      setLoading("loginBtn", false);
    }
  });
}

// ============================================
// SIGNUP FORM
// ============================================

const signupForm = document.getElementById("signupForm");
if (signupForm) {
  signupForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideError();

    const name = document.getElementById("name").value.trim();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const confirm = document.getElementById("confirm").value;

    // Validasi
    if (!name || !email || !password || !confirm) {
      showError("All fields are required");
      return;
    }

    if (password !== confirm) {
      showError("Passwords do not match");
      return;
    }

    if (password.length < 6) {
      showError("Password must be at least 6 characters");
      return;
    }

    // Validasi email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      showError("Please enter a valid email address");
      return;
    }

    setLoading("signupBtn", true);

    try {
      const response = await fetch("/api/auth/signup", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "same-origin",
        body: JSON.stringify({
          name,
          email,
          password,
          confirm_password: confirm,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        showError(data.error || "Signup failed. Please try again.");
        setLoading("signupBtn", false);
        return;
      }

      // Tampilkan sukses
      showSuccess("Account created! Redirecting to login...");

      // Redirect ke login
      setTimeout(() => {
        window.location.href = "/login";
      }, 1500);
    } catch (error) {
      console.error("Signup error:", error);
      showError("Network error. Please check your connection.");
      setLoading("signupBtn", false);
    }
  });
}

// ============================================
// LOGOUT FUNCTION
// ============================================

async function logoutUser() {
  try {
    await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "same-origin",
    });
  } catch (error) {
    console.error("Logout error:", error);
  }

  // Hapus data user dari localStorage
  localStorage.removeItem("aira_user");

  // Redirect ke login
  window.location.href = "/login";
}

// ============================================
// AUTH CHECK
// ============================================

async function checkAuth() {
  try {
    const response = await fetch("/api/auth/me", {
      credentials: "same-origin",
    });

    if (!response.ok) {
      window.location.href = "/login";
      return null;
    }

    const data = await response.json();
    localStorage.setItem("aira_user", JSON.stringify(data));
    return data;
  } catch (error) {
    console.error("Auth check error:", error);
    window.location.href = "/login";
    return null;
  }
}

// ============================================
// TOGGLE PASSWORD VISIBILITY
// ============================================

function togglePassword() {
  const passwordInput = document.getElementById("password");
  const toggleIcon = document.getElementById("toggleIcon");

  if (!passwordInput || !toggleIcon) return;

  if (passwordInput.type === "password") {
    passwordInput.type = "text";
    toggleIcon.classList.remove("fa-eye");
    toggleIcon.classList.add("fa-eye-slash");
  } else {
    passwordInput.type = "password";
    toggleIcon.classList.remove("fa-eye-slash");
    toggleIcon.classList.add("fa-eye");
  }
}

// ============================================
// EXPORT FUNCTIONS
// ============================================

window.logoutUser = logoutUser;
window.checkAuth = checkAuth;
window.togglePassword = togglePassword;
window.showError = showError;
window.showSuccess = showSuccess;
window.hideError = hideError;
window.setLoading = setLoading;

// ============================================
// INITIALIZATION
// ============================================

console.log("✅ Auth.js loaded successfully");
