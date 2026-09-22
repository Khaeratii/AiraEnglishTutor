// frontend/js/statistics.js

document.addEventListener("DOMContentLoaded", loadStats);

async function loadStats() {
  const content = document.getElementById("statsContent");

  try {
    const res = await fetch("/api/stats", { credentials: "same-origin" });
    if (!res.ok) {
      window.location.href = "/login";
      return;
    }
    const data = await res.json();

    if (!data.has_enough_data) {
      content.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-chart-line"></i>
                    <h3>Keep practicing</h3>
                    <p>${data.message || "Complete at least 5 conversations to unlock your progress statistics."}</p>
                    <div class="mini-stats">
                        <div class="mini-stat">
                            <span class="value">${data.total_conversations || 0}</span>
                            <span class="label">Conversations</span>
                        </div>
                        <div class="mini-stat">
                            <span class="value">${data.total_turns || 0}</span>
                            <span class="label">Turns</span>
                        </div>
                    </div>
                    <a href="/" class="btn-primary">Continue Practicing</a>
                </div>
            `;
      return;
    }

    renderStats(content, data);
  } catch (e) {
    content.innerHTML = `<div class="error-state">Failed to load statistics.</div>`;
  }
}

function renderStats(container, data) {
  const skills = data.skill_breakdown || {};
  const patterns = data.recurring_patterns || [];

  container.innerHTML = `
        <div class="stats-overview">
            <div class="overview-card primary">
                <div class="overview-label">Current Level</div>
                <div class="overview-value">${data.cefr_level.level}</div>
                <div class="overview-sub">${data.cefr_level.label}</div>
            </div>
            <div class="overview-card">
                <div class="overview-label">Overall Score</div>
                <div class="overview-value">${data.overall_score}</div>
                <div class="overview-sub">out of 100</div>
            </div>
            <div class="overview-card">
                <div class="overview-label">Conversations</div>
                <div class="overview-value">${data.total_conversations}</div>
                <div class="overview-sub">${data.total_turns} turns</div>
            </div>
            <div class="overview-card">
                <div class="overview-label">Total Words</div>
                <div class="overview-value">${data.total_words || 0}</div>
                <div class="overview-sub">avg ${data.avg_words_per_turn} / turn</div>
            </div>
        </div>
        
        <section class="dashboard-section">
            <h2>Skill Overview</h2>
            <div class="skills-grid">
                ${renderSkill("Grammar", skills.grammar)}
                ${renderSkill("Vocabulary", skills.vocabulary)}
                ${renderSkill("Fluency", skills.fluency)}
                ${renderSkill("Naturalness", skills.naturalness)}
                ${renderSkill("Communication", skills.communication)}
                ${renderSkill("Sentence Structure", skills.sentence_structure)}
            </div>
        </section>
        
        ${
          patterns.length > 0
            ? `
        <section class="dashboard-section">
            <h2>Recurring Patterns</h2>
            <p class="section-sub">Patterns detected across your conversations</p>
            <div class="patterns-list">
                ${patterns
                  .map(
                    (p) => `
                    <div class="pattern-item">
                        <div class="pattern-header">
                            <span class="pattern-name">${p.category}</span>
                            <span class="pattern-count">${p.frequency}×</span>
                        </div>
                        <div class="pattern-bar">
                            <div class="pattern-fill" style="width: ${Math.min(p.frequency * 15, 100)}%"></div>
                        </div>
                    </div>
                `,
                  )
                  .join("")}
            </div>
        </section>`
            : ""
        }
        
        <section class="dashboard-section">
            <h2>Conversation Ability</h2>
            <div class="ability-grid">
                <div class="ability-card">
                    <div class="ability-value">${data.conversation_ability?.explains_reasons || 0}%</div>
                    <div class="ability-label">Explains reasons</div>
                </div>
                <div class="ability-card">
                    <div class="ability-value">${data.conversation_ability?.expresses_opinions || 0}%</div>
                    <div class="ability-label">Expresses opinions</div>
                </div>
            </div>
        </section>
    `;
}

function renderSkill(name, skill) {
  if (!skill) return "";
  const score = skill.score || 0;

  let color = "#EF5350";
  if (score >= 80) color = "#4CAF50";
  else if (score >= 60) color = "#FFC107";

  return `
        <div class="skill-card">
            <div class="skill-header">
                <span class="skill-name">${name}</span>
                <span class="skill-score">${score}%</span>
            </div>
            <div class="skill-bar">
                <div class="skill-fill" style="width: ${score}%; background: ${color}"></div>
            </div>
            <div class="skill-detail">${renderSkillDetail(skill)}</div>
        </div>
    `;
}

function renderSkillDetail(skill) {
  if (skill.issue_count !== undefined)
    return `${skill.issue_count} issues detected`;
  if (skill.unique_words !== undefined)
    return `${skill.unique_words} unique words`;
  if (skill.avg_words !== undefined) return `avg ${skill.avg_words} words/turn`;
  return "";
}
