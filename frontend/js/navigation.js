// Shared responsive navigation behavior.
document.addEventListener("DOMContentLoaded", () => {
  const body = document.body;
  const openButton = document.querySelector(".mobile-nav-toggle");
  const closeButton = document.querySelector(".sidebar-close");
  const backdrop = document.querySelector(".sidebar-backdrop");
  const sidebar = document.querySelector(".sidebar, .dashboard-sidebar");
  const navLinks = sidebar?.querySelectorAll("a.nav-item") || [];
  const logoutButtons = document.querySelectorAll("[data-nav-logout]");

  if (!openButton || !sidebar) return;

  const setMenuOpen = (isOpen) => {
    body.classList.toggle("nav-open", isOpen);
    openButton.setAttribute("aria-expanded", String(isOpen));
    const isMobile = window.matchMedia("(max-width: 767px)").matches;
    sidebar.setAttribute("aria-hidden", String(isMobile && !isOpen));
  };

  openButton.addEventListener("click", () => {
    setMenuOpen(!body.classList.contains("nav-open"));
  });
  closeButton?.addEventListener("click", () => setMenuOpen(false));
  backdrop?.addEventListener("click", () => setMenuOpen(false));
  navLinks.forEach((link) =>
    link.addEventListener("click", () => setMenuOpen(false)),
  );
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setMenuOpen(false);
  });
  window.addEventListener("resize", () => {
    if (window.innerWidth >= 768) setMenuOpen(false);
  });

  const logout = async () => {
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "same-origin",
      });
    } finally {
      localStorage.removeItem("aira_user");
      window.location.href = "/login";
    }
  };

  logoutButtons.forEach((button) => button.addEventListener("click", logout));
  setMenuOpen(false);
});
