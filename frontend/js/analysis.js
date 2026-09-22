// frontend/js/analysis.js

document.addEventListener("DOMContentLoaded", loadAnalysis);

async function loadAnalysis() {
  const content = document.getElementById("analysisContent");
  content.innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>Analyzing today's practice...</p>
        </div>
    `;

  try {
    const res = await fetch("/api/analysis", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
    });

    if (res.status === 401) {
      window.location.href = "/login";
      return;
    }

    const data = await res.json();

    if (!res.ok) {
      throw new Error(
        data.message || data.error || "Analysis is temporarily unavailable.",
      );
    }

    if (!data.has_data) {
      content.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-clipboard-check"></i>
                    <h3>No practice data today yet</h3>
                    <p>${data.message || "Start a conversation with Aira to get your daily analysis."}</p>
                    <a href="/" class="btn-primary">Start Chatting</a>
                </div>
            `;
      return;
    }

    renderAnalysis(content, data);
    document.getElementById("analysisDate").textContent =
      `${data.date} · ${data.messages_count} messages · ${data.conversations_count} conversations`;
  } catch (e) {
    content.innerHTML = `
      <div class="error-state">
        <p>${escapeHtml(e.message || "Failed to load analysis.")}</p>
        <button class="btn-primary" type="button" onclick="loadAnalysis()">
          <i class="fas fa-sync"></i> Try Again
        </button>
      </div>`;
  }
}

function renderAnalysis(container, data) {
  const r = data.report;
  const e = data.evidence;

  container.innerHTML = `
        <section class="dashboard-section">
            <div class="overall-card">
                <div class="overall-icon"><i class="fas fa-star"></i></div>
                <div class="overall-text">
                    <h3>Overall Performance</h3>
                    <p>${r.overall?.summary || "Keep practicing!"}</p>
                    ${r.overall?.main_opportunity ? `<p class="opportunity">Main opportunity: ${r.overall.main_opportunity}</p>` : ""}
                </div>
            </div>
        </section>
        
        <section class="dashboard-section">
            <h2>Today's Highlights</h2>
            <div class="highlights-grid">
                <div class="highlight-card">
                    <div class="highlight-icon grammar"><i class="fas fa-spell-check"></i></div>
                    <div class="highlight-value">${r.highlights?.grammar_issues_count || 0}</div>
                    <div class="highlight-label">Grammar issues</div>
                </div>
                <div class="highlight-card">
                    <div class="highlight-icon naturalness"><i class="fas fa-comment-dots"></i></div>
                    <div class="highlight-value">${r.highlights?.naturalness_improvements_count || 0}</div>
                    <div class="highlight-label">Naturalness</div>
                </div>
                <div class="highlight-card">
                    <div class="highlight-icon vocab"><i class="fas fa-book"></i></div>
                    <div class="highlight-value">${e.vocabulary?.total_unique || 0}</div>
                    <div class="highlight-label">Unique words</div>
                </div>
                <div class="highlight-card">
                    <div class="highlight-icon conversation"><i class="fas fa-comments"></i></div>
                    <div class="highlight-value">${data.messages_count}</div>
                    <div class="highlight-label">Messages today</div>
                </div>
            </div>
        </section>
        
        ${
          r.strengths && r.strengths.length
            ? `
        <section class="dashboard-section">
            <h2><i class="fas fa-trophy"></i> What You Did Well</h2>
            <div class="strengths-list">
                ${r.strengths
                  .map(
                    (s) => `
                    <div class="strength-item">
                        <div class="strength-icon"><i class="fas fa-check-circle"></i></div>
                        <div>
                            <strong>${s.title}</strong>
                            <p>${s.description}</p>
                        </div>
                    </div>
                `,
                  )
                  .join("")}
            </div>
        </section>`
            : ""
        }
        
        ${
          r.corrections && r.corrections.length
            ? `
        <section class="dashboard-section">
            <h2><i class="fas fa-pen"></i> Grammar & Naturalness</h2>
            <div class="corrections-list">
                ${r.corrections
                  .map(
                    (c) => `
                    <div class="correction-card ${c.type}">
                        <div class="correction-type">${c.type === "grammar" ? "Grammar" : "Naturalness"}</div>
                        <div class="correction-row">
                            <span class="correction-label">You said:</span>
                            <span class="correction-original">${escapeHtml(c.original)}</span>
                        </div>
                        <div class="correction-row">
                            <span class="correction-label">Better:</span>
                            <span class="correction-better">${escapeHtml(c.better)}</span>
                        </div>
                        <div class="correction-why"><strong>Why:</strong> ${escapeHtml(c.why)}</div>
                    </div>
                `,
                  )
                  .join("")}
            </div>
        </section>`
            : ""
        }
        
        ${
          e.vocabulary?.unique_words?.length
            ? `
        <section class="dashboard-section">
            <h2><i class="fas fa-book"></i> Today's Vocabulary</h2>
            <div class="vocab-tags">
                ${e.vocabulary.unique_words
                  .slice(0, 20)
                  .map((w) => `<span class="vocab-tag">${w}</span>`)
                  .join("")}
            </div>
        </section>`
            : ""
        }
        
        ${
          r.today_focus && r.today_focus.length
            ? `
        <section class="dashboard-section">
            <h2><i class="fas fa-target"></i> Today's Focus</h2>
            <div class="focus-list">
                ${r.today_focus
                  .map(
                    (f) => `
                    <div class="focus-item">
                        <div class="focus-number">${f.priority}</div>
                        <div>
                            <strong>${f.area}</strong>
                            <p>${f.reason}</p>
                        </div>
                    </div>
                `,
                  )
                  .join("")}
            </div>
        </section>`
            : ""
        }
        
        ${
          r.practice && r.practice.length
            ? `
        <section class="dashboard-section">
            <h2><i class="fas fa-dumbbell"></i> Practice</h2>
            <div class="practice-list">
                ${r.practice
                  .map(
                    (p, i) => `
                    <div class="practice-item">
                        <div class="practice-num">${i + 1}</div>
                        <div class="practice-sentence">${escapeHtml(p.sentence)}</div>
                        <div class="practice-hint">Hint: ${escapeHtml(p.hint)}</div>
                    </div>
                `,
                  )
                  .join("")}
            </div>
        </section>`
            : ""
        }
    `;
}

function escapeHtml(t) {
  const d = document.createElement("div");
  d.textContent = t || "";
  return d.innerHTML;
}
