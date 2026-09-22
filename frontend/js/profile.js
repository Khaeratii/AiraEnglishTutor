document.addEventListener("DOMContentLoaded", async () => {
  const message = document.getElementById("profileMessage");
  try {
    const response = await fetch("/api/profile", {
      credentials: "same-origin",
    });
    if (!response.ok) {
      window.location.href = "/login";
      return;
    }
    const data = await response.json();
    document.getElementById("profileName").textContent = data.name || "";
    document.getElementById("profileGreeting").textContent =
      `Welcome back, ${data.name || "learner"}`;
    document.getElementById("profileAvatar").textContent = (data.name || "A")
      .charAt(0)
      .toUpperCase();
    document.getElementById("profileEmailHero").textContent = data.email || "";
    document.getElementById("profileEmailDetail").textContent =
      data.email || "";
    document.getElementById("profileCreated").textContent = data.created_at
      ? new Date(data.created_at).toLocaleDateString()
      : "";
    document.getElementById("profileLevel").textContent =
      data.level_label || data.level || "Learner";
    document.getElementById("profileConversations").textContent =
      data.learning?.conversations || 0;
    document.getElementById("profileMessages").textContent =
      data.learning?.messages || 0;
    document.getElementById("profileTurns").textContent =
      data.learning?.turns || 0;
    document.getElementById("profileEvents").textContent =
      data.learning?.learning_events || 0;
  } catch (error) {
    message.textContent = "Could not load your profile.";
  }

  document
    .getElementById("changePasswordForm")
    .addEventListener("submit", async (event) => {
      event.preventDefault();
      const currentPassword = document.getElementById("currentPassword");
      const newPassword = document.getElementById("newPassword");
      const confirmPassword = document.getElementById("confirmPassword");
      message.textContent = "";
      if (newPassword.value.length < 6) {
        message.textContent = "New password must be 6+ characters.";
        return;
      }
      if (newPassword.value !== confirmPassword.value) {
        message.textContent = "New passwords do not match.";
        return;
      }
      try {
        const response = await fetch("/api/profile/change-password", {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            current_password: currentPassword.value,
            new_password: newPassword.value,
            confirm_password: confirmPassword.value,
          }),
        });
        const data = await response.json();
        message.textContent = data.message || "Unable to change password.";
        message.className = `profile-message ${response.ok ? "success" : "error"}`;
        if (response.ok) document.getElementById("changePasswordForm").reset();
      } catch (error) {
        message.textContent = "Unable to change password. Please try again.";
      }
    });

  document
    .getElementById("logoutProfile")
    .addEventListener("click", async () => {
      await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "same-origin",
      });
      window.location.href = "/login";
    });
});
