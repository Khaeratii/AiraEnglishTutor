// frontend/js/history.js

document.addEventListener("DOMContentLoaded", loadHistory);

async function loadHistory() {
  const content = document.getElementById("historyContent");

  try {
    const res = await fetch("/api/conversations", {
      credentials: "same-origin",
    });
    if (!res.ok) {
      window.location.href = "/login";
      return;
    }
    const data = await res.json();

    if (!data.conversations || data.conversations.length === 0) {
      content.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-comments"></i>
                    <h3>No conversations yet</h3>
                    <p>Start chatting with Aira to begin your English journey.</p>
                    <a href="/" class="btn-primary">Start Chatting</a>
                </div>
            `;
      return;
    }

    content.innerHTML = `<div class="history-list">
            ${data.conversations.map((c) => renderConversation(c)).join("")}
        </div>`;
  } catch (e) {
    content.innerHTML = `<div class="error-state">Failed to load history.</div>`;
  }
}

function renderConversation(conv) {
  const date = new Date(conv.updated_at);
  const dateStr = date.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  const timeStr = date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });

  return `
        <div class="history-item" data-id="${conv.id}" onclick="openConversation('${conv.id}')">
            <div class="history-icon"><i class="fas fa-comment"></i></div>
            <div class="history-info">
                <h3>${escapeHtml(conv.title || "Conversation")}</h3>
                <div class="history-meta">
                    <span><i class="fas fa-calendar"></i> ${dateStr}</span>
                    <span><i class="fas fa-clock"></i> ${timeStr}</span>
                    <span><i class="fas fa-comments"></i> ${conv.turn_count || 0} turns</span>
                </div>
            </div>
            <button class="btn-delete" onclick="deleteConv('${conv.id}', event)">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `;
}

function openConversation(id) {
  window.location.href = `/?conversation_id=${encodeURIComponent(id)}`;
}

async function deleteConv(id, e) {
  e.stopPropagation();
  if (!confirm("Delete this conversation?")) return;

  try {
    await fetch(`/api/conversations/${id}`, {
      method: "DELETE",
      credentials: "same-origin",
    });
    loadHistory();
  } catch (err) {
    alert("Failed to delete");
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
