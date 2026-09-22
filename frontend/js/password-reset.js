function setResetMessage(message, success = false) {
  const element = document.getElementById("errorMessage");
  if (!element) return;
  element.textContent = message;
  element.className = `${success ? "success-message" : "error-message"} show`;
}

const forgotForm = document.getElementById("forgotForm");
if (forgotForm) {
  forgotForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("email").value.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setResetMessage("Please enter a valid email address.");
      return;
    }
    setLoading("forgotBtn", true);
    try {
      const response = await fetch("/api/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await response.json();
      setResetMessage(
        data.message ||
          "If an account with that email exists, we've sent instructions to reset your password.",
        true,
      );
    } catch (error) {
      setResetMessage(
        "We could not process that request. Please try again later.",
      );
    } finally {
      setLoading("forgotBtn", false);
    }
  });
}

const resetForm = document.getElementById("resetForm");
if (resetForm) {
  resetForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const password = document.getElementById("password").value;
    const confirm = document.getElementById("confirm").value;
    if (password.length < 6)
      return setResetMessage("Password must be 6+ characters.");
    if (password !== confirm) return setResetMessage("Passwords do not match.");
    setLoading("resetBtn", true);
    try {
      const token = window.location.pathname.split("/").pop();
      const response = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password, confirm_password: confirm }),
      });
      const data = await response.json();
      if (!response.ok)
        setResetMessage(data.message || "This reset link is invalid.");
      else {
        setResetMessage(data.message, true);
        setTimeout(() => {
          window.location.href = "/login";
        }, 1500);
      }
    } catch (error) {
      setResetMessage(
        "We could not process that request. Please try again later.",
      );
    } finally {
      setLoading("resetBtn", false);
    }
  });
}
