// frontend/js/app.js
// ============================================
// AIRA - MAIN APPLICATION LOGIC
// ============================================

// ============================================
// STATE
// ============================================

let activeConversationId = null; // Current conversation ID
let chatCount = 0;
let maxRequests = 20;
let isProcessing = false;
let isResetting = false;

// ============================================
// DOM ELEMENTS
// ============================================

const messagesContainer = document.getElementById("messagesContainer");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const voiceBtn = document.getElementById("voiceBtn");
const progressFill = document.getElementById("progressFill");
const progressText = document.getElementById("progressText");
const totalChats = document.getElementById("totalChats");
const avgInput = document.getElementById("avgInput");
const levelDisplay = document.getElementById("levelDisplay");
const resetBtn = document.getElementById("resetBtn");
const newChatBtn = document.getElementById("newChatBtn");
const logoutBtn = document.getElementById("logoutBtn");
const analysisPanel = document.getElementById("analysisPanel");
const analysisContent = document.getElementById("analysisContent");
const closeAnalysis = document.getElementById("closeAnalysis");

// ============================================
// AUTH CHECK
// ============================================

(async function initAuth() {
  try {
    const response = await fetch("/api/auth/me", {
      credentials: "same-origin",
    });

    if (!response.ok) {
      window.location.href = "/login";
      return;
    }

    const user = await response.json();
    localStorage.setItem("aira_user", JSON.stringify(user));

    if (levelDisplay) {
      levelDisplay.textContent = user.level_label || "Beginner";
    }

    console.log("✅ User authenticated:", user.name);
  } catch (error) {
    console.error("Auth check failed:", error);
    window.location.href = "/login";
  }
})();

// ============================================
// LOGOUT
// ============================================

function logout() {
  if (confirm("Are you sure you want to sign out?")) {
    fetch("/api/auth/logout", {
      method: "POST",
      credentials: "same-origin",
    })
      .then(() => {
        localStorage.removeItem("aira_user");
        window.location.href = "/login";
      })
      .catch(() => {
        localStorage.removeItem("aira_user");
        window.location.href = "/login";
      });
  }
}

// ============================================
// TOAST
// ============================================

function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

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

// ============================================
// API HELPER
// ============================================

async function apiRequest(endpoint, options = {}) {
  const response = await fetch(`/api${endpoint}`, {
    ...options,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const requestError = new Error(error.error || error.message || "API Error");
    requestError.status = response.status;
    requestError.retryable = Boolean(error.retryable);
    requestError.userMessage = error.message;
    requestError.conversationId = error.conversation_id;
    throw requestError;
  }

  return response.json();
}

// ============================================
// CHAT
// ============================================

async function sendMessage(message) {
  if (!message || !message.trim()) return;
  if (isProcessing || isResetting) return;

  isProcessing = true;

  addMessage("user", message.trim());
  messageInput.value = "";
  showTyping();

  try {
    const data = await apiRequest("/chat", {
      method: "POST",
      body: JSON.stringify({
        message: message.trim(),
        conversation_id: activeConversationId, // Send current ID
      }),
    });

    hideTyping();
    addMessage("ai", data.response);

    // Update active conversation ID if server created one
    if (data.conversation_id && data.conversation_id !== activeConversationId) {
      activeConversationId = data.conversation_id;
      console.log("📝 Active conversation:", activeConversationId);
    }

    // Show analysis if any
    if (data.analysis) {
      setTimeout(() => {
        addMessage("ai", "📝 " + data.analysis);
      }, 800);
    }

    playAudio(data.response);

    chatCount = data.turns || chatCount + 1;
    maxRequests = data.max_requests || 20;
    updateProgress();
    loadStats();
  } catch (error) {
    hideTyping();
    if (error.conversationId) {
      activeConversationId = error.conversationId;
    }
    if (error.message.includes("limit")) {
      addMessage("ai", "We've had a great session! Let's continue tomorrow.");
    } else if (error.retryable || error.status === 503) {
      addMessage(
        "ai",
        "Aira is having a little trouble reaching the AI service right now. Your message wasn't lost — please try again in a moment.",
      );
    } else {
      addMessage("ai", "Sorry, something went wrong. Please try again.");
    }
    console.error("Error:", error);
  } finally {
    isProcessing = false;
  }
}

// ============================================
// MESSAGE UI
// ============================================

function addMessage(type, content) {
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${type}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar-small";
  avatar.innerHTML =
    type === "ai"
      ? '<i class="fas fa-robot"></i>'
      : '<i class="fas fa-user"></i>';

  const contentDiv = document.createElement("div");
  contentDiv.className = "message-content";

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = content;

  const time = document.createElement("div");
  time.className = "message-time";
  time.textContent = new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  contentDiv.appendChild(bubble);
  contentDiv.appendChild(time);
  messageDiv.appendChild(avatar);
  messageDiv.appendChild(contentDiv);

  messagesContainer.appendChild(messageDiv);
  scrollToBottom();
}

function showTyping() {
  const typingDiv = document.createElement("div");
  typingDiv.className = "message ai typing-indicator";
  typingDiv.id = "typingIndicator";
  typingDiv.innerHTML = `
        <div class="avatar-small"><i class="fas fa-robot"></i></div>
        <div class="message-content">
            <div class="message-bubble">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
  messagesContainer.appendChild(typingDiv);
  scrollToBottom();
}

function hideTyping() {
  const typing = document.getElementById("typingIndicator");
  if (typing) typing.remove();
}

function scrollToBottom() {
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function showWelcomeMessage() {
  messagesContainer.innerHTML = `
        <div class="message ai">
            <div class="avatar-small">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="message-bubble">
                    Hello! I'm Aira, your English conversation partner. Let's start speaking!
                </div>
                <div class="message-time">Just now</div>
            </div>
        </div>
    `;
}

// ============================================
// AUDIO
// ============================================

async function playAudio(text) {
  try {
    const response = await fetch("/api/tts", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) throw new Error("TTS failed");

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.play();
  } catch (error) {
    console.error("TTS Error:", error);
  }
}

// ============================================
// UI UPDATES
// ============================================

function updateProgress() {
  const percentage = Math.min((chatCount / maxRequests) * 100, 100);
  if (progressFill) progressFill.style.width = `${percentage}%`;
  if (progressText) progressText.textContent = `${chatCount}/${maxRequests}`;
}

async function loadStats() {
  try {
    const stats = await apiRequest("/stats");
    if (totalChats) totalChats.textContent = stats.total || 0;
    if (avgInput) avgInput.textContent = stats.avg_user || 0;
  } catch (error) {
    console.error("Stats error:", error);
  }
}

async function loadSelectedConversation() {
  const conversationId = new URLSearchParams(window.location.search).get(
    "conversation_id",
  );
  if (!conversationId) return;
  try {
    const data = await apiRequest(
      `/conversations/${encodeURIComponent(conversationId)}`,
    );
    activeConversationId = conversationId;
    messagesContainer.innerHTML = "";
    for (const message of data.messages || []) {
      addMessage(message.role === "user" ? "user" : "ai", message.content);
    }
  } catch (error) {
    console.error("Conversation load error:", error);
    showToast("This conversation could not be opened.", "error");
  }
}

// ============================================
// RESET SESSION (FIXED)
// ============================================

async function resetSession() {
  if (isResetting || isProcessing) return;

  // Check if current session has messages
  const hasMessages = messagesContainer.querySelectorAll(".message").length > 1;

  if (hasMessages) {
    if (
      !confirm(
        "Start a new conversation?\n\nYour current conversation will be saved to History.",
      )
    ) {
      return;
    }
  }

  isResetting = true;

  // Disable both reset & new chat buttons
  const buttons = [resetBtn, newChatBtn].filter(Boolean);
  buttons.forEach((b) => (b.disabled = true));

  console.log("🔄 Reset session requested");
  console.log("   old_conversation_id=" + activeConversationId);

  try {
    const response = await apiRequest("/conversations/reset", {
      method: "POST",
      body: JSON.stringify({
        current_conversation_id: activeConversationId,
      }),
    });

    if (!response.success) {
      throw new Error(response.message || "Reset failed");
    }

    console.log("✅ Reset successful");
    console.log("   new_conversation_id=" + response.conversation_id);

    // Clear frontend state
    activeConversationId = response.conversation_id;
    chatCount = 0;

    // Clear UI
    messagesContainer.innerHTML = "";
    showWelcomeMessage();
    updateProgress();

    // Focus input
    if (messageInput) {
      messageInput.focus();
      messageInput.value = "";
    }

    showToast(
      "New session started! Previous conversation saved to History.",
      "success",
    );
    loadStats();
  } catch (error) {
    console.error("❌ Reset failed:", error);
    showToast(
      "Couldn't start a new session. Your current conversation is still safe.",
      "error",
    );
  } finally {
    isResetting = false;
    buttons.forEach((b) => (b.disabled = false));
  }
}

// ============================================
// NEW CHAT (alias for Reset)
// ============================================

function newChat() {
  resetSession();
}

// ============================================
// ANALYSIS PANEL
// ============================================

async function getAnalysis() {
  if (!analysisPanel) return;

  analysisPanel.classList.add("active");
  analysisContent.innerHTML =
    '<div class="loading"><div class="spinner"></div><p>Loading...</p></div>';

  try {
    const data = await apiRequest("/analysis", { method: "POST" });

    if (data.has_enough_data === false) {
      analysisContent.innerHTML = `<p>${data.message || "Not enough data yet."}</p>`;
      return;
    }

    const formatted = (data.analysis || "No analysis available.")
      .replace(/\n/g, "<br>")
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/### (.*?)/g, "<h4>$1</h4>");

    analysisContent.innerHTML = formatted;
  } catch (error) {
    analysisContent.innerHTML =
      "<p>Error getting analysis. Please try again.</p>";
    console.error("Analysis Error:", error);
  }
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener("DOMContentLoaded", () => {
  loadStats();
  updateProgress();
  loadSelectedConversation();

  // Logout
  if (logoutBtn) logoutBtn.addEventListener("click", logout);

  // Voice
  if (voiceBtn) {
    voiceBtn.addEventListener("click", () => {
      if (typeof startRecording === "function") {
        startRecording();
      } else {
        console.warn("startRecording not loaded");
      }
    });
  }

  // Send
  if (sendBtn) {
    sendBtn.addEventListener("click", () => {
      const message = messageInput.value.trim();
      if (message) sendMessage(message);
    });
  }

  // Enter
  if (messageInput) {
    messageInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (message) sendMessage(message);
      }
    });
  }

  // Reset button
  if (resetBtn) resetBtn.addEventListener("click", resetSession);

  // New chat button
  if (newChatBtn) newChatBtn.addEventListener("click", newChat);

  // Close analysis
  if (closeAnalysis) {
    closeAnalysis.addEventListener("click", () => {
      analysisPanel.classList.remove("active");
    });
  }

  // Escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      analysisPanel?.classList.remove("active");
    }
  });

  // Click outside
  if (analysisPanel) {
    analysisPanel.addEventListener("click", (e) => {
      if (e.target === analysisPanel) {
        analysisPanel.classList.remove("active");
      }
    });
  }
});

console.log("✅ App.js loaded");
