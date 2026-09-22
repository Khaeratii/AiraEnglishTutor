// frontend/js/ui.js
// UI utility functions

// Toast notification system
// frontend/js/ui.js
// ============================================
// UI UTILITIES
// ============================================

function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) {
    console.warn("Toast container not found");
    return;
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;

  const icons = {
    success: "fa-check-circle",
    error: "fa-exclamation-circle",
    warning: "fa-exclamation-triangle",
    info: "fa-info-circle",
  };

  toast.innerHTML = `
        <i class="fas ${icons[type] || icons.info}"></i>
        <span>${message}</span>
    `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("fade-out");
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text || "";
  return div.innerHTML;
}

console.log("✅ UI.js loaded");

function getIconForType(type) {
  const icons = {
    success: "fa-check-circle",
    error: "fa-exclamation-circle",
    warning: "fa-exclamation-triangle",
    info: "fa-info-circle",
  };
  return icons[type] || icons.info;
}

// Add toast styles dynamically
const toastStyles = `
.toast {
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 12px 20px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 14px;
    font-weight: 500;
    z-index: 10000;
    animation: slideInRight 0.3s ease;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}

.toast i {
    font-size: 20px;
}

.toast-success {
    background: #4CAF50;
    color: white;
}

.toast-error {
    background: #f44336;
    color: white;
}

.toast-warning {
    background: #FFC107;
    color: #333;
}

.toast-info {
    background: #6C63FF;
    color: white;
}

.toast.fade-out {
    animation: fadeOut 0.3s ease forwards;
}

@keyframes slideInRight {
    from {
        opacity: 0;
        transform: translateX(50px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

@keyframes fadeOut {
    from {
        opacity: 1;
        transform: translateX(0);
    }
    to {
        opacity: 0;
        transform: translateX(50px);
    }
}
`;

// Add styles to document
const styleSheet = document.createElement("style");
styleSheet.textContent = toastStyles;
document.head.appendChild(styleSheet);

// Format analysis text with proper styling
function formatAnalysis(text) {
  return text
    .replace(/\n/g, "<br>")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/### (.*?)/g, "<h4>$1</h4>")
    .replace(/\|/g, "")
    .replace(/---/g, "");
}

// Handle text input auto-resize
function autoResize(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = Math.min(textarea.scrollHeight, 150) + "px";
}

// Copy text to clipboard
function copyToClipboard(text) {
  navigator.clipboard
    .writeText(text)
    .then(() => {
      showToast("Copied to clipboard!", "success");
    })
    .catch(() => {
      // Fallback
      const textarea = document.createElement("textarea");
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      showToast("Copied to clipboard!", "success");
    });
}
// frontend/js/ui.js
// UI Utilities

// Toast styles sudah ada di CSS
// Fungsi showToast ada di app.js

// Tambahkan fungsi utility lainnya

function formatTime(date) {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function scrollToBottom(element) {
  if (element) {
    element.scrollTop = element.scrollHeight;
  }
}
