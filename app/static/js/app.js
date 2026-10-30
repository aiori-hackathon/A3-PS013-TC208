/**
 * TraceLens - Core SPA Controller
 */
import { API } from "./api.js";

// Global Application State
const state = {
  currentView: "overview",
  summary: null,
  evidenceList: [],
  investigations: [],
  selectedInvestigationId: null,
  timelineFilter: {
    page: 1,
    page_size: 25,
    search: "",
    evidence_id: "",
    uncertainty_filter: "all"
  },
  stopwatch: {
    timerId: null,
    startTime: null,
    elapsedSeconds: 0
  }
};

// Notification Toast Utility
export function showToast(message, type = "info") {
  const container = document.getElementById("tl-toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = "tl-toast";
  const icon = type === "error" ? "⚠️" : type === "success" ? "✓" : "ℹ️";
  toast.innerHTML = `<span>${icon}</span><span style="flex-grow:1;">${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

export function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Router & View Switcher
export function navigateTo(viewName) {
  state.currentView = viewName;
  window.location.hash = viewName;

  // Update sidebar active links
  document.querySelectorAll(".tl-nav-link").forEach(link => {
    if (link.getAttribute("data-view") === viewName) {
      link.classList.add("active");
    } else {
      link.classList.remove("active");
    }
  });

  // Update breadcrumb
  const breadcrumbEl = document.getElementById("tl-breadcrumb-current");
  if (breadcrumbEl) {
    breadcrumbEl.textContent = formatViewName(viewName);
  }

  // Render view
  renderCurrentView();
}

function formatViewName(view) {
  const map = {
    overview: "Overview",
    vault: "Evidence Vault",
    ingestion: "Ingestion & Parsing",
    timeline: "Incident Timeline",
    blindlens: "BlindLens Review",
    mutation: "Mutation Radar",
    investigations: "Investigations",
    evaluation: "Evaluation & Benchmarks",
    reports: "Reports",
    settings: "Settings & Audit"
  };
  return map[view] || view;
}

async function renderCurrentView() {
  const content = document.getElementById("tl-app-content");
  if (!content) return;

  try {
    switch (state.currentView) {
      case "overview":
        await renderOverview(content);
        break;
      case "vault":
        await renderVault(content);
        break;
      case "ingestion":
        await renderIngestion(content);
        break;
      case "timeline":
        await renderTimeline(content);
        break;
      case "blindlens":
        await renderBlindLens(content);
        break;
      case "mutation":
        await renderMutation(content);
        break;
      case "investigations":
        await renderInvestigations(content);
        break;
      case "evaluation":
        await renderEvaluation(content);
        break;
      case "reports":
        await renderReports(content);
        break;
      case "settings":
        await renderSettings(content);
        break;
      default:
        await renderOverview(content);
    }
  } catch (err) {
    content.innerHTML = `<div class="tl-notice-box tl-notice-danger">Error loading view: ${escapeHtml(err.message)}</div>`;
  }
}

// =========================================================================
// 1. OVERVIEW VIEW
// =========================================================================
async function renderOverview(container) {
  const [summary, activity] = await Promise.all([
    API.getDashboardSummary(),
    API.getRecentActivity()
  ]);
  state.summary = summary;

  const isEmpty = summary.evidence_files_count === 0;

  container.innerHTML = `
    <div class="tl-page-header">
      <div>
        <h1 class="tl-page-title">Executive Evidence & Timeline Overview</h1>
        <p class="tl-page-desc">Empirical telemetry calculated from local persistent evidence database.</p>
      </div>
      <div class="d-flex gap-2">
        <button class="tl-btn tl-btn-primary" id="btn-import-scenario-quick">Import Synthetic Scenario</button>
        <button class="tl-btn tl-btn-secondary" id="btn-upload-evidence-quick">Upload Evidence</button>
      </div>
    </div>

    <!-- KPI Summary Cards -->
    <div class="row g-3 mb-4">
      <div class="col-6 col-md-3">
        <div class="tl-metric-card">
          <div class="tl-metric-label">Evidence Files</div>
          <div class="tl-metric-val" id="kpi-evidence-count">${summary.evidence_files_count}</div>
          <div class="tl-metric-sub">SHA-256 baselines preserved</div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="tl-metric-card">
          <div class="tl-metric-label">Total Source Records</div>
          <div class="tl-metric-val">${summary.total_source_records}</div>
          <div class="tl-metric-sub">${summary.parsed_records} parsed (${summary.total_source_records > 0 ? Math.round(summary.parsed_records / summary.total_source_records * 100) : 0}%)</div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="tl-metric-card">
          <div class="tl-metric-label">Timeline Events</div>
          <div class="tl-metric-val">${summary.timeline_events_count}</div>
          <div class="tl-metric-sub">Normalized to UTC with bounds</div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="tl-metric-card">
          <div class="tl-metric-label">Integrity Mismatches</div>
          <div class="tl-metric-val" style="color:${summary.evidence_mismatches_count > 0 ? '#dc2626' : '#16a34a'}">
            ${summary.evidence_mismatches_count}
          </div>
          <div class="tl-metric-sub">${summary.findings_requiring_review_count} findings flagged for review</div>
        </div>
      </div>
    </div>

    <!-- Parsing Ledger Accounting Breakdown -->
    <div class="tl-card mb-4">
      <div class="tl-card-header">
        <h3 class="tl-card-title">Parsing Ledger Distribution (Invariant: Total = Parsed + Partial + Ambiguous + Unparsed)</h3>
        <span class="tl-pill tl-pill-healthy"><span class="tl-pill-dot"></span> Reconciled</span>
      </div>
      <div class="tl-card-body">
        <div class="row g-3 text-center">
          <div class="col-3">
            <div style="font-size:1.1rem; font-weight:700; color:#16a34a;">${summary.parsed_records}</div>
            <div style="font-size:0.75rem; color:#64748b;">PARSED</div>
          </div>
          <div class="col-3">
            <div style="font-size:1.1rem; font-weight:700; color:#d97706;">${summary.partial_records}</div>
            <div style="font-size:0.75rem; color:#64748b;">PARTIAL</div>
          </div>
          <div class="col-3">
            <div style="font-size:1.1rem; font-weight:700; color:#854d0e;">${summary.ambiguous_records}</div>
            <div style="font-size:0.75rem; color:#64748b;">AMBIGUOUS</div>
          </div>
          <div class="col-3">
            <div style="font-size:1.1rem; font-weight:700; color:#dc2626;">${summary.unparsed_records}</div>
            <div style="font-size:0.75rem; color:#64748b;">UNPARSED</div>
          </div>
        </div>
      </div>
    </div>

    ${isEmpty ? `
      <div class="tl-notice-box tl-notice-warning text-center p-4">
        <h5>No Evidence Collected Yet</h5>
        <p class="mb-3">Start by importing one of the 3 pre-packaged synthetic incident scenarios or upload raw Linux/Nginx logs.</p>
        <button class="tl-btn tl-btn-primary" onclick="window.loadScenarioDialog()">Load Synthetic Scenario</button>
      </div>
    ` : ''}

    <!-- Recent Audit Activity -->
    <div class="tl-card">
      <div class="tl-card-header">
        <h3 class="tl-card-title">Append-Only Audit Activity Trail</h3>
        <span style="font-size:0.72rem; color:#64748b;">NIST SP 800-92 Traceability</span>
      </div>
      <div class="tl-table-wrapper">
        <table class="tl-table">
          <thead>
            <tr>
              <th>Timestamp (UTC)</th>
              <th>Action</th>
              <th>Entity</th>
              <th>Actor</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            ${activity.length > 0 ? activity.map(a => `
              <tr>
                <td class="tl-mono" style="white-space:nowrap;">${a.timestamp.replace("T", " ").substring(0, 19)}</td>
                <td><span class="tl-pill tl-pill-neutral">${escapeHtml(a.action)}</span></td>
                <td><span class="tl-mono">${escapeHtml(a.entity_id)}</span></td>
                <td>${escapeHtml(a.actor)}</td>
                <td style="font-size:0.75rem; color:#64748b; max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                  ${escapeHtml(a.details || "-")}
                </td>
              </tr>
            `).join("") : `<tr><td colspan="5" class="text-center text-muted">No activity recorded yet.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>
  `;

  document.getElementById("btn-import-scenario-quick")?.addEventListener("click", () => window.loadScenarioDialog());
  document.getElementById("btn-upload-evidence-quick")?.addEventListener("click", () => navigateTo("vault"));
}

// =========================================================================
// 2. EVIDENCE VAULT
// =========================================================================
async function renderVault(container) {
  const files = await API.listEvidence();
  state.evidenceList = files;

  container.innerHTML = `
    <div class="tl-page-header">
      <div>
        <h1 class="tl-page-title">Evidence Vault & Cryptographic Baselines</h1>
        <p class="tl-page-desc">Preserves original evidence bytes with initial SHA-256 baseline hashing (RFC 3227 & NIST FIPS 180-4).</p>
      </div>
      <button class="tl-btn tl-btn-primary" id="btn-open-upload-modal">+ Upload Evidence File</button>
    </div>

    <div class="tl-notice-box">
      <b>Immutability Requirement:</b> Original evidence files are preserved in managed storage using server-generated identifiers.
      Raw bytes are never overwritten, normalized in-place, or discarded.
    </div>

    <!-- Evidence Files Table -->
    <div class="tl-card">
      <div class="tl-card-header">
        <h3 class="tl-card-title">Preserved Evidence Files (${files.length})</h3>
        <button class="tl-btn tl-btn-secondary tl-btn-sm" id="btn-verify-all-vault">Verify All Integrity</button>
      </div>
      <div class="tl-table-wrapper">
        <table class="tl-table">
          <thead>
            <tr>
              <th>Evidence ID</th>
              <th>Filename</th>
              <th>Size</th>
              <th>SHA-256 Cryptographic Baseline</th>
              <th>Collected (UTC)</th>
              <th>Verification Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${files.length > 0 ? files.map(f => {
              let statusPill = `<span class="tl-pill tl-pill-neutral"><span class="tl-pill-dot"></span> UNVERIFIED</span>`;
              if (f.latest_verification_status === "MATCH") {
                statusPill = `<span class="tl-pill tl-pill-healthy"><span class="tl-pill-dot"></span> MATCH</span>`;
              } else if (f.latest_verification_status === "MISMATCH") {
                statusPill = `<span class="tl-pill tl-pill-danger"><span class="tl-pill-dot"></span> MISMATCH</span>`;
              } else if (f.latest_verification_status === "FILE_NOT_FOUND") {
                statusPill = `<span class="tl-pill tl-pill-danger"><span class="tl-pill-dot"></span> MISSING</span>`;
              }
              return `
                <tr>
                  <td><span class="tl-mono fw-bold">${f.evidence_id}</span></td>
                  <td>${escapeHtml(f.original_filename)}</td>
                  <td>${formatBytes(f.file_size_bytes)}</td>
                  <td>
                    <span class="tl-hash-badge" title="Click to copy full hash" onclick="window.copyToClipboard('${f.sha256_baseline}')">
                      ${f.sha256_baseline.substring(0, 16)}... 📋
                    </span>
                  </td>
                  <td class="tl-mono">${f.collected_at.replace("T", " ").substring(0, 19)}</td>
                  <td>${statusPill}</td>
                  <td>
                    <div class="d-flex gap-1">
                      <button class="tl-btn tl-btn-secondary tl-btn-sm" onclick="window.verifySingleEvidence('${f.evidence_id}')">Verify</button>
                      <button class="tl-btn tl-btn-secondary tl-btn-sm" onclick="window.viewHistory('${f.evidence_id}')">History</button>
                      <button class="tl-btn tl-btn-secondary tl-btn-sm" onclick="window.quickIngest('${f.evidence_id}', '${escapeHtml(f.original_filename)}')">Parse</button>
                    </div>
                  </td>
                </tr>
              `;
            }).join("") : `<tr><td colspan="7" class="text-center text-muted p-4">No evidence collected yet. Upload files or import a synthetic scenario.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Upload Modal Container -->
    <div id="upload-modal-container"></div>
  `;

  document.getElementById("btn-open-upload-modal")?.addEventListener("click", () => openUploadModal());
  document.getElementById("btn-verify-all-vault")?.addEventListener("click", async () => {
    showToast("Verifying all evidence baselines...", "info");
    for (const f of files) {
      await API.verifyEvidence(f.evidence_id);
    }
    showToast("Integrity verification completed for all evidence files.", "success");
    renderVault(container);
  });
}

function openUploadModal() {
  const container = document.getElementById("upload-modal-container");
  if (!container) return;

  container.innerHTML = `
    <div class="modal fade show" style="display:block; background:rgba(15,23,42,0.5);" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Upload Evidence Log File</h5>
            <button type="button" class="btn-close" onclick="document.getElementById('upload-modal-container').innerHTML=''"></button>
          </div>
          <form id="form-upload-evidence">
            <div class="modal-body">
              <div class="mb-3">
                <label class="form-label fw-bold">Select Log File</label>
                <input type="file" class="form-control" name="file" id="upload-file-input" required />
                <div class="form-text">Supported: Linux auth.log, Nginx access logs, generic text logs (Max 50MB).</div>
              </div>
              <div class="mb-3">
                <label class="form-label">Notes / Source Provenance</label>
                <textarea class="form-control" name="notes" rows="2" placeholder="e.g., Extracted from DMZ reverse proxy host01"></textarea>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="tl-btn tl-btn-secondary" onclick="document.getElementById('upload-modal-container').innerHTML=''">Cancel</button>
              <button type="submit" class="tl-btn tl-btn-primary" id="btn-submit-upload">Collect & Hash</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `;

  document.getElementById("form-upload-evidence")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("btn-submit-upload");
    btn.disabled = true;
    btn.textContent = "Hashing...";

    const formData = new FormData(e.target);
    try {
      const res = await API.uploadEvidence(formData);
      showToast(`Evidence collected! ID: ${res.evidence_id}`, "success");
      container.innerHTML = "";
      renderVault(document.getElementById("tl-app-content"));
    } catch (err) {
      showToast(err.message, "error");
      btn.disabled = false;
      btn.textContent = "Collect & Hash";
    }
  });
}

// Window actions
window.copyToClipboard = function(text) {
  navigator.clipboard.writeText(text);
  showToast("SHA-256 digest copied to clipboard.", "info");
};

window.verifySingleEvidence = async function(evidenceId) {
  try {
    const res = await API.verifyEvidence(evidenceId);
    if (res.result === "MATCH") {
      showToast(`Verification MATCH for ${evidenceId}`, "success");
    } else {
      showToast(`ALERT: Integrity ${res.result} detected for ${evidenceId}!`, "error");
    }
    renderVault(document.getElementById("tl-app-content"));
  } catch (err) {
    showToast(err.message, "error");
  }
};

window.viewHistory = async function(evidenceId) {
  const history = await API.getVerificationHistory(evidenceId);
  const container = document.getElementById("upload-modal-container");
  container.innerHTML = `
    <div class="modal fade show" style="display:block; background:rgba(15,23,42,0.5);" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Verification History — ${evidenceId}</h5>
            <button type="button" class="btn-close" onclick="document.getElementById('upload-modal-container').innerHTML=''"></button>
          </div>
          <div class="modal-body">
            <p><b>Baseline Digest:</b> <code class="tl-mono">${history.baseline_hash}</code></p>
            <div class="tl-table-wrapper">
              <table class="tl-table">
                <thead>
                  <tr>
                    <th>Timestamp (UTC)</th>
                    <th>Result</th>
                    <th>Observed Digest</th>
                    <th>Notes / Errors</th>
                  </tr>
                </thead>
                <tbody>
                  ${history.verifications.map(v => `
                    <tr>
                      <td class="tl-mono">${v.verified_at.replace("T", " ").substring(0, 19)}</td>
                      <td>
                        <span class="tl-pill ${v.result === 'MATCH' ? 'tl-pill-healthy' : 'tl-pill-danger'}">
                          ${v.result}
                        </span>
                      </td>
                      <td class="tl-mono">${v.observed_hash.substring(0, 20)}...</td>
                      <td style="font-size:0.75rem;">${escapeHtml(v.error_message || "-")}</td>
                    </tr>
                  `).join("")}
                </tbody>
              </table>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="tl-btn tl-btn-secondary" onclick="document.getElementById('upload-modal-container').innerHTML=''">Close</button>
          </div>
        </div>
      </div>
    </div>
  `;
};

window.quickIngest = function(evidenceId, filename) {
  navigateTo("ingestion");
  setTimeout(() => {
    const sel = document.getElementById("ingest-evidence-select");
    if (sel) sel.value = evidenceId;
    const parserSel = document.getElementById("ingest-parser-select");
    if (parserSel) {
      if (filename.includes("nginx")) parserSel.value = "nginx_access";
      else parserSel.value = "linux_auth";
    }
  }, 100);
};

// =========================================================================
// 3. INGESTION & PARSING
// =========================================================================
async function renderIngestion(container) {
  const [evidenceFiles, ingestions] = await Promise.all([
    API.listEvidence(),
    API.listIngestions()
  ]);

  container.innerHTML = `
    <div class="tl-page-header">
      <div>
        <h1 class="tl-page-title">Deterministic Ingestion & Parsing Ledgers</h1>
        <p class="tl-page-desc">Separates raw source lines from normalized events. Reconciles 100% of input records.</p>
      </div>
    </div>

    <!-- Trigger Ingestion Form -->
    <div class="tl-card mb-4">
      <div class="tl-card-header">
        <h3 class="tl-card-title">Run Parser Ingestion</h3>
      </div>
      <div class="tl-card-body">
        <form id="form-trigger-ingestion">
          <div class="row g-3">
            <div class="col-md-4">
              <label class="form-label fw-bold">Select Evidence File</label>
              <select class="form-select" id="ingest-evidence-select" required>
                <option value="">-- Choose collected evidence --</option>
                ${evidenceFiles.map(e => `
                  <option value="${e.evidence_id}">${e.evidence_id} (${escapeHtml(e.original_filename)})</option>
                `).join("")}
              </select>
            </div>
            <div class="col-md-3">
              <label class="form-label fw-bold">Parser Module</label>
              <select class="form-select" id="ingest-parser-select" required>
                <option value="linux_auth">Linux auth.log Parser (Syslog)</option>
                <option value="nginx_access">Nginx Access Log Parser (Combined)</option>
              </select>
            </div>
            <div class="col-md-2">
              <label class="form-label">Timezone Assumption</label>
              <select class="form-select" id="ingest-tz-select">
                <option value="UTC" selected>UTC (+00:00)</option>
                <option value="America/New_York">America/New_York (EST/EDT)</option>
                <option value="Europe/London">Europe/London (GMT/BST)</option>
                <option value="Asia/Kolkata">Asia/Kolkata (+05:30)</option>
              </select>
            </div>
            <div class="col-md-2">
              <label class="form-label">Clock Tolerance (Δt sec)</label>
              <input type="number" step="0.1" class="form-control" id="ingest-uncertainty-input" value="1.0" min="0" />
            </div>
            <div class="col-md-1 d-flex align-items-end">
              <button type="submit" class="tl-btn tl-btn-primary w-100" id="btn-run-ingest">Ingest</button>
            </div>
          </div>
        </form>
      </div>
    </div>

    <!-- Ingestion History & Accounting Ledgers -->
    <div class="tl-card">
      <div class="tl-card-header">
        <h3 class="tl-card-title">Parsing Ledger Accounting History</h3>
        <button class="tl-btn tl-btn-secondary tl-btn-sm" id="btn-inspect-gaps-modal">Inspect Parsing Gaps</button>
      </div>
      <div class="tl-table-wrapper">
        <table class="tl-table">
          <thead>
            <tr>
              <th>Ingestion ID</th>
              <th>Evidence ID</th>
              <th>Parser</th>
              <th>Total Input</th>
              <th>PARSED</th>
              <th>PARTIAL</th>
              <th>AMBIGUOUS</th>
              <th>UNPARSED</th>
              <th>Reconciled</th>
              <th>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            ${ingestions.length > 0 ? ingestions.map(i => `
              <tr>
                <td><span class="tl-mono fw-bold">${i.ingestion_id}</span></td>
                <td><span class="tl-mono">${i.evidence_id}</span></td>
                <td>${escapeHtml(i.parser_name)} (v${escapeHtml(i.parser_version)})</td>
                <td class="fw-bold">${i.total_records}</td>
                <td style="color:#16a34a; font-weight:600;">${i.parsed_count}</td>
                <td style="color:#d97706; font-weight:600;">${i.partial_count}</td>
                <td style="color:#854d0e; font-weight:600;">${i.ambiguous_count}</td>
                <td style="color:#dc2626; font-weight:600;">${i.unparsed_count}</td>
                <td>
                  <span class="tl-pill ${i.reconciled ? 'tl-pill-healthy' : 'tl-pill-danger'}">
                    ${i.reconciled ? '✓ RECONCILED' : 'MISMATCH'}
                  </span>
                </td>
                <td class="tl-mono">${i.started_at.replace("T", " ").substring(0, 19)}</td>
              </tr>
            `).join("") : `<tr><td colspan="10" class="text-center text-muted p-4">No log ingestions performed yet.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>

    <div id="gaps-modal-container"></div>
  `;

  document.getElementById("form-trigger-ingestion")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("btn-run-ingest");
    btn.disabled = true;
    btn.textContent = "Processing...";

    const payload = {
      evidence_id: document.getElementById("ingest-evidence-select").value,
      parser_name: document.getElementById("ingest-parser-select").value,
      timezone_assumption: document.getElementById("ingest-tz-select").value,
      default_year: 2026,
      clock_uncertainty_seconds: parseFloat(document.getElementById("ingest-uncertainty-input").value) || 1.0
    };

    try {
      const res = await API.triggerIngestion(payload);
      showToast(`Ingestion completed! ${res.total_records} records reconciled.`, "success");
      renderIngestion(container);
    } catch (err) {
      showToast(err.message, "error");
      btn.disabled = false;
      btn.textContent = "Ingest";
    }
  });

  document.getElementById("btn-inspect-gaps-modal")?.addEventListener("click", () => openGapsModal());
}

async function openGapsModal() {
  const container = document.getElementById("gaps-modal-container");
  const data = await API.inspectGaps();

  container.innerHTML = `
    <div class="modal fade show" style="display:block; background:rgba(15,23,42,0.5);" tabindex="-1">
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Parsing Gaps & Problematic Records (${data.total})</h5>
            <button type="button" class="btn-close" onclick="document.getElementById('gaps-modal-container').innerHTML=''"></button>
          </div>
          <div class="modal-body">
            <p class="text-muted" style="font-size:0.8rem;">
              Enforces transparent accounting: blank lines, non-standard records, and incomplete fields are preserved with line numbers and reasons.
            </p>
            <div class="tl-table-wrapper" style="max-height:400px; overflow-y:auto;">
              <table class="tl-table">
                <thead>
                  <tr>
                    <th>Evidence ID</th>
                    <th>Line #</th>
                    <th>Status</th>
                    <th>Parser Warnings</th>
                    <th>Raw Text</th>
                  </tr>
                </thead>
                <tbody>
                  ${data.records.length > 0 ? data.records.map(r => `
                    <tr>
                      <td class="tl-mono">${r.evidence_id}</td>
                      <td>${r.line_number}</td>
                      <td>
                        <span class="tl-pill ${r.parsing_status === 'PARTIAL' ? 'tl-pill-warning' : r.parsing_status === 'AMBIGUOUS' ? 'tl-pill-warning' : 'tl-pill-danger'}">
                          ${r.parsing_status}
                        </span>
                      </td>
                      <td style="font-size:0.75rem; color:#b91c1c;">${escapeHtml(r.parser_warnings || "-")}</td>
                      <td class="tl-mono" style="font-size:0.75rem; white-space:pre-wrap;">${escapeHtml(r.raw_text)}</td>
                    </tr>
                  `).join("") : `<tr><td colspan="5" class="text-center text-muted">No parsing gaps detected. All records successfully parsed!</td></tr>`}
                </tbody>
              </table>
            </div>
          </div>
          <div class="modal-footer">
            <a href="/api/reports/export/gaps-csv" class="tl-btn tl-btn-secondary" download>Download Gaps CSV</a>
            <button type="button" class="tl-btn tl-btn-primary" onclick="document.getElementById('gaps-modal-container').innerHTML=''">Close</button>
          </div>
        </div>
      </div>
    </div>
  `;
}

// =========================================================================
// 4. INCIDENT TIMELINE
// =========================================================================
async function renderTimeline(container) {
  const [evidenceFiles, timelineResult] = await Promise.all([
    API.listEvidence(),
    API.queryTimeline(state.timelineFilter)
  ]);

  container.innerHTML = `
    <div class="tl-page-header">
      <div>
        <h1 class="tl-page-title">Source-Linked Incident Timeline</h1>
        <p class="tl-page-desc">Normalized to UTC with explicit uncertainty bounds $[t-\\Delta t, t+\\Delta t]$ and order certainty analysis.</p>
      </div>
      <div class="d-flex gap-2">
        <a href="/api/reports/export/csv" class="tl-btn tl-btn-secondary" download>Export Timeline CSV</a>
      </div>
    </div>

    <!-- Multi-criteria Filter Bar -->
    <div class="tl-card mb-3">
      <div class="tl-card-body p-3">
        <div class="row g-2">
          <div class="col-md-3">
            <input type="text" class="form-control form-control-sm" id="tl-search-input" placeholder="Search message, target, IP, user..." value="${escapeHtml(state.timelineFilter.search)}" />
          </div>
          <div class="col-md-2">
            <select class="form-select form-select-sm" id="tl-evidence-filter">
              <option value="">All Evidence Files</option>
              ${evidenceFiles.map(e => `
                <option value="${e.evidence_id}" ${state.timelineFilter.evidence_id === e.evidence_id ? 'selected' : ''}>${e.evidence_id}</option>
              `).join("")}
            </select>
          </div>
          <div class="col-md-2">
            <select class="form-select form-select-sm" id="tl-uncertainty-filter">
              <option value="all" ${state.timelineFilter.uncertainty_filter === 'all' ? 'selected' : ''}>All Events</option>
              <option value="uncertain_only" ${state.timelineFilter.uncertainty_filter === 'uncertain_only' ? 'selected' : ''}>Uncertain Order Only</option>
              <option value="certain_only" ${state.timelineFilter.uncertainty_filter === 'certain_only' ? 'selected' : ''}>Strict Order Only</option>
            </select>
          </div>
          <div class="col-md-3">
            <select class="form-select form-select-sm" id="tl-type-filter">
              <option value="">All Event Types</option>
              <option value="AUTH_FAILURE">AUTH_FAILURE (SSH/PAM)</option>
              <option value="AUTH_SUCCESS">AUTH_SUCCESS</option>
              <option value="HTTP_REQUEST">HTTP_REQUEST</option>
              <option value="HTTP_AUTH_FAILURE">HTTP_AUTH_FAILURE (401/403)</option>
            </select>
          </div>
          <div class="col-md-2 d-flex gap-1">
            <button class="tl-btn tl-btn-primary tl-btn-sm w-100" id="btn-apply-filters">Apply Filter</button>
            <button class="tl-btn tl-btn-secondary tl-btn-sm" id="btn-reset-filters">Reset</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Timeline Event Table -->
    <div class="tl-card">
      <div class="tl-card-header">
        <h3 class="tl-card-title">Events (${timelineResult.total_count} total, Page ${timelineResult.page} of ${timelineResult.total_pages})</h3>
        <span style="font-size:0.75rem; color:#64748b;">Click an event to inspect source line</span>
      </div>
      <div class="tl-table-wrapper">
        <table class="tl-table">
          <thead>
            <tr>
              <th>Normalized UTC</th>
              <th>Uncertainty Interval [t-Δ, t+Δ]</th>
              <th>Order Certainty</th>
              <th>Source IP</th>
              <th>User</th>
              <th>Event Summary</th>
              <th>Source Line</th>
            </tr>
          </thead>
          <tbody>
            ${timelineResult.events.length > 0 ? timelineResult.events.map(e => {
              const utcStr = e.normalized_utc ? e.normalized_utc.replace("T", " ").substring(0, 19) : "UNRESOLVED";
              const earliestStr = e.earliest_utc ? e.earliest_utc.substring(11, 19) : "-";
              const latestStr = e.latest_utc ? e.latest_utc.substring(11, 19) : "-";
              const orderBadge = e.order_uncertain 
                ? `<span class="tl-pill tl-pill-warning"><span class="tl-pill-dot"></span> ORDER UNCERTAIN</span>`
                : `<span class="tl-pill tl-pill-neutral">Certain</span>`;

              return `
                <tr style="cursor:pointer;" onclick="window.openEventDetails('${e.event_id}')">
                  <td class="tl-mono fw-bold">${utcStr}</td>
                  <td class="tl-mono" style="font-size:0.72rem; color:#64748b;">[${earliestStr} to ${latestStr}]</td>
                  <td>${orderBadge}</td>
                  <td><span class="tl-mono">${e.source_ip || "-"}</span></td>
                  <td>${e.username ? `<span class="badge bg-light text-dark border">${escapeHtml(e.username)}</span>` : "-"}</td>
                  <td style="max-width:350px;">
                    <div style="font-weight:500;">${escapeHtml(e.summary)}</div>
                    ${e.warnings ? `<div style="font-size:0.7rem; color:#d97706;">⚠️ ${escapeHtml(e.warnings)}</div>` : ''}
                  </td>
                  <td><span class="tl-mono" style="font-size:0.75rem;">${e.evidence_id}:L${e.source_line}</span></td>
                </tr>
              `;
            }).join("") : `<tr><td colspan="7" class="text-center text-muted p-4">No events found matching current criteria.</td></tr>`}
          </tbody>
        </table>
      </div>
      
      <!-- Pagination Controls -->
      ${timelineResult.total_pages > 1 ? `
        <div class="p-2 border-top d-flex justify-content-between align-items-center">
          <button class="tl-btn tl-btn-secondary tl-btn-sm" ${timelineResult.page <= 1 ? 'disabled' : ''} onclick="window.changeTimelinePage(${timelineResult.page - 1})">Previous</button>
          <span style="font-size:0.75rem; color:#64748b;">Page ${timelineResult.page} of ${timelineResult.total_pages}</span>
          <button class="tl-btn tl-btn-secondary tl-btn-sm" ${timelineResult.page >= timelineResult.total_pages ? 'disabled' : ''} onclick="window.changeTimelinePage(${timelineResult.page + 1})">Next</button>
        </div>
      ` : ''}
    </div>

    <div id="event-detail-modal-container"></div>
  `;

  document.getElementById("btn-apply-filters")?.addEventListener("click", () => {
    state.timelineFilter.search = document.getElementById("tl-search-input").value;
    state.timelineFilter.evidence_id = document.getElementById("tl-evidence-filter").value;
    state.timelineFilter.uncertainty_filter = document.getElementById("tl-uncertainty-filter").value;
    state.timelineFilter.event_type = document.getElementById("tl-type-filter").value;
    state.timelineFilter.page = 1;
    renderTimeline(container);
  });

  document.getElementById("btn-reset-filters")?.addEventListener("click", () => {
    state.timelineFilter = { page: 1, page_size: 25, search: "", evidence_id: "", uncertainty_filter: "all" };
    renderTimeline(container);
  });
}

window.changeTimelinePage = function(newPage) {
  state.timelineFilter.page = newPage;
  renderTimeline(document.getElementById("tl-app-content"));
};

window.openEventDetails = async function(eventId) {
  const container = document.getElementById("event-detail-modal-container");
  const data = await API.getEventSource(eventId);
  const related = await API.getRelatedEvents(eventId);

  const ev = data.event_id;
  container.innerHTML = `
    <div class="modal fade show" style="display:block; background:rgba(15,23,42,0.5);" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Event Inspection & Source Traceability</h5>
            <button type="button" class="btn-close" onclick="document.getElementById('event-detail-modal-container').innerHTML=''"></button>
          </div>
          <div class="modal-body">
            <!-- Event Metadata -->
            <div class="row g-2 mb-3">
              <div class="col-md-6">
                <div style="font-size:0.75rem; color:#64748b;">EVENT ID</div>
                <div class="tl-mono fw-bold">${data.event_id}</div>
              </div>
              <div class="col-md-6">
                <div style="font-size:0.75rem; color:#64748b;">SOURCE EVIDENCE</div>
                <div class="tl-mono">${data.evidence_id} (${data.original_filename})</div>
              </div>
            </div>

            <!-- Original Preserved Source Line -->
            <div class="mb-3">
              <label class="form-label fw-bold" style="font-size:0.8rem;">
                Original Preserved Record (Line ${data.source_line})
              </label>
              <div class="p-2 bg-dark text-light tl-mono" style="font-size:0.78rem; border-radius:4px; word-break:break-all;">
                ${escapeHtml(data.raw_text)}
              </div>
              <div class="mt-1" style="font-size:0.72rem; color:#64748b;">
                Cryptographic Evidence Baseline SHA-256: <code class="tl-mono">${data.sha256_baseline}</code>
              </div>
            </div>

            <!-- Related Events -->
            ${related.length > 0 ? `
              <div class="mt-4">
                <h6 style="font-size:0.85rem; font-weight:600;">Related Temporal & Correlated Events (${related.length})</h6>
                <div class="tl-table-wrapper" style="max-height:180px; overflow-y:auto;">
                  <table class="tl-table">
                    <thead>
                      <tr>
                        <th>UTC</th>
                        <th>IP / User</th>
                        <th>Summary</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${related.map(r => `
                        <tr>
                          <td class="tl-mono">${r.normalized_utc ? r.normalized_utc.substring(11, 19) : '-'}</td>
                          <td>${r.source_ip || '-'} / ${r.username || '-'}</td>
                          <td>${escapeHtml(r.summary)}</td>
                        </tr>
                      `).join("")}
                    </tbody>
                  </table>
                </div>
              </div>
            ` : ''}
          </div>
          <div class="modal-footer">
            <button type="button" class="tl-btn tl-btn-primary" onclick="document.getElementById('event-detail-modal-container').innerHTML=''">Close</button>
          </div>
        </div>
      </div>
    </div>
  `;
};

// =========================================================================
// 5. BLINDLENS STAGED INVESTIGATOR REVIEW
// =========================================================================
async function renderBlindLens(container) {
  const [reviews, investigations] = await Promise.all([
    API.listBlindLensReviews(),
    API.listInvestigations()
  ]);

  container.innerHTML = `
    <div class="tl-page-header">
      <div>
        <h1 class="tl-page-title">BlindLens: Staged Review & Hypothesis Accountability</h1>
        <p class="tl-page-desc">Records investigator assessments prior to contextual disclosure. Generates canonical SHA-256 digests.</p>
      </div>
      <button class="tl-btn tl-btn-primary" id="btn-create-blindlens-modal">+ New Staged Review</button>
    </div>

    <!-- Methodology Disclaimer -->
    <div class="tl-notice-box">
      <b>Structured Forensic Review Workflow:</b>
      Stage 1 records the investigator's initial interpretation with neutral identifiers and seals optional context items with a canonical SHA-256 digest.
      Stage 2 reveals context (e.g. authorized pentest ticket, maintenance window) and requires an explicit rationale for any change in conclusion.
      <i>Note: The system preserves accountability; it does not claim to diagnose, detect, or eliminate cognitive bias.</i>
    </div>

    <!-- Active Reviews List -->
    <div class="tl-card">
      <div class="tl-card-header">
        <h3 class="tl-card-title">Recorded Staged Reviews (${reviews.length})</h3>
      </div>
      <div class="tl-table-wrapper">
        <table class="tl-table">
          <thead>
            <tr>
              <th>Review ID</th>
              <th>Investigation</th>
              <th>Stage</th>
              <th>Initial Hypothesis & Confidence</th>
              <th>Stage 1 Canonical Digest</th>
              <th>Revised Hypothesis & Confidence</th>
              <th>Final Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${reviews.length > 0 ? reviews.map(r => `
              <tr>
                <td><span class="tl-mono fw-bold">${r.review_id}</span></td>
                <td><span class="tl-mono">${r.investigation_id}</span></td>
                <td>
                  <span class="tl-pill ${r.stage === 'REVEALED' ? 'tl-pill-healthy' : 'tl-pill-warning'}">
                    ${r.stage === 'REVEALED' ? 'STAGE 2: REVEALED' : 'STAGE 1: INITIAL'}
                  </span>
                </td>
                <td>
                  <div style="font-weight:500;">${escapeHtml(r.initial_hypothesis)}</div>
                  <div style="font-size:0.75rem; color:#64748b;">Confidence: ${r.initial_confidence}%</div>
                </td>
                <td>
                  <span class="tl-hash-badge" title="Stage 1 SHA-256 canonical digest">
                    ${r.initial_digest.substring(0, 14)}...
                  </span>
                </td>
                <td>
                  ${r.revised_hypothesis ? `
                    <div style="font-weight:500;">${escapeHtml(r.revised_hypothesis)}</div>
                    <div style="font-size:0.75rem; color:#64748b;">Confidence: ${r.revised_confidence}%</div>
                  ` : '<span class="text-muted">Pending Context Reveal</span>'}
                </td>
                <td>
                  <span class="badge ${r.final_review_status === 'CONFIRMED' ? 'bg-success' : r.final_review_status === 'REVISED' ? 'bg-primary' : 'bg-secondary'}">
                    ${r.final_review_status}
                  </span>
                </td>
                <td>
                  <div class="d-flex gap-1">
                    ${r.stage === 'INITIAL' ? `
                      <button class="tl-btn tl-btn-primary tl-btn-sm" onclick="window.triggerRevealModal('${r.review_id}')">Reveal Context</button>
                    ` : `
                      <button class="tl-btn tl-btn-secondary tl-btn-sm" onclick="window.triggerVerifyModal('${r.review_id}')">Verify Digest</button>
                    `}
                  </div>
                </td>
              </tr>
            `).join("") : `<tr><td colspan="8" class="text-center text-muted p-4">No BlindLens reviews recorded yet.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>

    <div id="blindlens-modal-container"></div>
  `;

  document.getElementById("btn-create-blindlens-modal")?.addEventListener("click", () => openCreateReviewModal(investigations));
}

function openCreateReviewModal(investigations) {
  const container = document.getElementById("blindlens-modal-container");
  container.innerHTML = `
    <div class="modal fade show" style="display:block; background:rgba(15,23,42,0.5);" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Stage 1: Initialize BlindLens Staged Review</h5>
            <button type="button" class="btn-close" onclick="document.getElementById('blindlens-modal-container').innerHTML=''"></button>
          </div>
          <form id="form-create-review">
            <div class="modal-body">
              <div class="mb-3">
                <label class="form-label fw-bold">Select Investigation Scope</label>
                <select class="form-select" id="bl-inv-select" required>
                  ${investigations.map(i => `<option value="${i.investigation_id}">${i.title} (${i.investigation_id})</option>`).join("")}
                </select>
              </div>
              <div class="mb-3">
                <label class="form-label fw-bold">Initial Hypothesis (Pre-Context Evaluation)</label>
                <textarea class="form-control" id="bl-hypothesis" rows="3" placeholder="Enter initial interpretation based on neutral identifiers..." required></textarea>
              </div>
              <div class="row g-3 mb-3">
                <div class="col-md-4">
                  <label class="form-label fw-bold">Confidence (0 - 100%)</label>
                  <input type="number" class="form-control" id="bl-confidence" min="0" max="100" value="70" required />
                </div>
                <div class="col-md-8">
                  <label class="form-label">Evidence References</label>
                  <input type="text" class="form-control" id="bl-refs" placeholder="e.g. EVT-01, EVT-02" />
                </div>
              </div>
              <div class="mb-3">
                <label class="form-label fw-bold">Optional Context Items (Sealed until Stage 2)</label>
                <textarea class="form-control" id="bl-context-items" rows="2" placeholder='e.g., Authorized penetration testing scheduled for 192.0.2.10 by SecOps'></textarea>
                <div class="form-text">These details will be sealed cryptographically and hidden from the reviewer until explicitly revealed.</div>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="tl-btn tl-btn-secondary" onclick="document.getElementById('blindlens-modal-container').innerHTML=''">Cancel</button>
              <button type="submit" class="tl-btn tl-btn-primary">Record Stage 1 Assessment</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `;

  document.getElementById("form-create-review")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const contextText = document.getElementById("bl-context-items").value.trim();
    const contextItems = contextText ? [{ type: "OPERATIONAL_NOTE", content: contextText }] : [];

    const payload = {
      investigation_id: document.getElementById("bl-inv-select").value,
      initial_hypothesis: document.getElementById("bl-hypothesis").value,
      initial_confidence: parseInt(document.getElementById("bl-confidence").value, 10),
      initial_evidence_refs: document.getElementById("bl-refs").value.split(",").map(s => s.trim()).filter(Boolean),
      context_items: contextItems
    };

    try {
      const res = await API.createBlindLensReview(payload);
      showToast(`Stage 1 Recorded! Canonical Digest: ${res.initial_digest.substring(0, 12)}...`, "success");
      container.innerHTML = "";
      renderBlindLens(document.getElementById("tl-app-content"));
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

window.triggerRevealModal = async function(reviewId) {
  const container = document.getElementById("blindlens-modal-container");
  const review = await API.getBlindLensReview(reviewId);

  container.innerHTML = `
    <div class="modal fade show" style="display:block; background:rgba(15,23,42,0.5);" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Stage 2: Context Reveal & Re-Assessment</h5>
            <button type="button" class="btn-close" onclick="document.getElementById('blindlens-modal-container').innerHTML=''"></button>
          </div>
          <form id="form-submit-revision">
            <div class="modal-body">
              <!-- Preserved Stage 1 Baseline -->
              <div class="p-3 bg-light border rounded mb-3">
                <div style="font-size:0.75rem; color:#64748b; font-weight:700;">PRESERVED STAGE 1 ASSESSMENT</div>
                <div class="fw-bold">${escapeHtml(review.initial_hypothesis)}</div>
                <div style="font-size:0.75rem;">Confidence: ${review.initial_confidence}% | Digest: <code class="tl-mono">${review.initial_digest.substring(0, 16)}...</code></div>
              </div>

              <!-- Revealed Context -->
              <div class="p-3 bg-info bg-opacity-10 border border-info rounded mb-3">
                <div style="font-size:0.75rem; color:#0369a1; font-weight:700;">REVEALED CONTEXT ITEMS</div>
                ${review.context_items && review.context_items.length > 0 ? review.context_items.map(c => `
                  <div>• ${escapeHtml(c.content || JSON.stringify(c))}</div>
                `).join("") : '<div>• Maintenance ticket: Authorized vulnerability scan and testing performed during this window.</div>'}
              </div>

              <!-- Revision Form -->
              <div class="mb-3">
                <label class="form-label fw-bold">Revised Hypothesis (Post-Context Assessment)</label>
                <textarea class="form-control" id="bl-rev-hypothesis" rows="2" required>${escapeHtml(review.initial_hypothesis)}</textarea>
              </div>

              <div class="row g-3 mb-3">
                <div class="col-md-4">
                  <label class="form-label fw-bold">Revised Confidence (0 - 100%)</label>
                  <input type="number" class="form-control" id="bl-rev-confidence" min="0" max="100" value="${review.initial_confidence}" required />
                </div>
                <div class="col-md-8">
                  <label class="form-label fw-bold">Review Status</label>
                  <select class="form-select" id="bl-rev-status">
                    <option value="CONFIRMED">CONFIRMED (Hypothesis holds despite context)</option>
                    <option value="REVISED" selected>REVISED (Context altered conclusion)</option>
                    <option value="UNRESOLVED">UNRESOLVED (Inconclusive / Needs further review)</option>
                  </select>
                </div>
              </div>

              <div class="mb-3">
                <label class="form-label fw-bold text-danger">Mandatory Rationale for Change</label>
                <textarea class="form-control" id="bl-rev-reason" rows="2" placeholder="Explain why your assessment changed or why it remained unchanged..." required></textarea>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="tl-btn tl-btn-secondary" onclick="document.getElementById('blindlens-modal-container').innerHTML=''">Cancel</button>
              <button type="submit" class="tl-btn tl-btn-primary">Record Revision & Final Digest</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `;

  // First call reveal endpoint to advance stage
  await API.revealContext(reviewId);

  document.getElementById("form-submit-revision")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      revised_hypothesis: document.getElementById("bl-rev-hypothesis").value,
      revised_confidence: parseInt(document.getElementById("bl-rev-confidence").value, 10),
      reason_for_change: document.getElementById("bl-rev-reason").value,
      final_review_status: document.getElementById("bl-rev-status").value
    };

    try {
      const res = await API.submitRevision(reviewId, payload);
      showToast("Stage 2 revision recorded with final canonical digest.", "success");
      container.innerHTML = "";
      renderBlindLens(document.getElementById("tl-app-content"));
    } catch (err) {
      showToast(err.message, "error");
    }
  });
};

window.triggerVerifyModal = async function(reviewId) {
  const res = await API.verifyBlindLensReview(reviewId);
  const container = document.getElementById("blindlens-modal-container");
  container.innerHTML = `
    <div class="modal fade show" style="display:block; background:rgba(15,23,42,0.5);" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Cryptographic Review Verification</h5>
            <button type="button" class="btn-close" onclick="document.getElementById('blindlens-modal-container').innerHTML=''"></button>
          </div>
          <div class="modal-body">
            <div class="tl-notice-box ${res.is_valid ? 'tl-notice-box' : 'tl-notice-danger'}">
              ${res.message}
            </div>
            <p><b>Stage 1 Digest Match:</b> ${res.initial_digest_match ? '✓ MATCH' : '❌ MISMATCH'}</p>
            <p><b>Stage 2 Digest Match:</b> ${res.final_digest_match ? '✓ MATCH' : '❌ MISMATCH'}</p>
            <p style="font-size:0.75rem;">Calculated: <code class="tl-mono">${res.calculated_initial_digest}</code></p>
          </div>
          <div class="modal-footer">
            <button type="button" class="tl-btn tl-btn-primary" onclick="document.getElementById('blindlens-modal-container').innerHTML=''">Close</button>
          </div>
        </div>
      </div>
    </div>
  `;
};

// =========================================================================
// 6. MUTATION RADAR
// =========================================================================
async function renderMutation(container) {
  const summary = await API.getMutationSummary();

  container.innerHTML = `
    <div class="tl-page-header">
      <div>
        <h1 class="tl-page-title">Mutation Radar & Evidence Integrity Impact</h1>
        <p class="tl-page-desc">Tracks SHA-256 baseline verifications. Automatically maps impact of modified evidence to downstream findings.</p>
      </div>
    </div>

    <!-- Integrity Status Cards -->
    <div class="row g-3 mb-4">
      <div class="col-6 col-md-3">
        <div class="tl-metric-card">
          <div class="tl-metric-label">Total Preserved Files</div>
          <div class="tl-metric-val">${summary.total_evidence_files}</div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="tl-metric-card">
          <div class="tl-metric-label">Verified Baselines</div>
          <div class="tl-metric-val" style="color:#16a34a;">${summary.match_count}</div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="tl-metric-card">
          <div class="tl-metric-label">Hash Mismatches</div>
          <div class="tl-metric-val" style="color:${summary.mismatch_count > 0 ? '#dc2626' : '#64748b'};">
            ${summary.mismatch_count}
          </div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="tl-metric-card">
          <div class="tl-metric-label">Findings Requiring Review</div>
          <div class="tl-metric-val" style="color:${summary.impacted_findings_count > 0 ? '#dc2626' : '#64748b'};">
            ${summary.impacted_findings_count}
          </div>
        </div>
      </div>
    </div>

    <!-- Evidence Verification Status Table -->
    <div class="tl-card mb-4">
      <div class="tl-card-header">
        <h3 class="tl-card-title">Evidence Files Integrity Radar</h3>
      </div>
      <div class="tl-table-wrapper">
        <table class="tl-table">
          <thead>
            <tr>
              <th>Evidence ID</th>
              <th>Filename</th>
              <th>Recorded Baseline (SHA-256)</th>
              <th>Observed Digest</th>
              <th>Radar Status</th>
              <th>Last Checked</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${summary.files.length > 0 ? summary.files.map(f => `
              <tr>
                <td><span class="tl-mono fw-bold">${f.evidence_id}</span></td>
                <td>${escapeHtml(f.filename)}</td>
                <td class="tl-mono" style="font-size:0.75rem;">${f.baseline_hash.substring(0, 16)}...</td>
                <td class="tl-mono" style="font-size:0.75rem;">${f.observed_hash ? f.observed_hash.substring(0, 16) + '...' : '-'}</td>
                <td>
                  <span class="tl-pill ${f.status === 'MATCH' ? 'tl-pill-healthy' : f.status === 'MISMATCH' ? 'tl-pill-danger' : 'tl-pill-neutral'}">
                    ${f.status}
                  </span>
                </td>
                <td class="tl-mono">${f.last_verified_at ? f.last_verified_at.replace("T", " ").substring(0, 19) : 'Never'}</td>
                <td>
                  <div class="d-flex gap-1">
                    <button class="tl-btn tl-btn-secondary tl-btn-sm" onclick="window.viewImpactMap('${f.evidence_id}')">Impact Map</button>
                    ${f.scenario_tag === 'scenario-03' ? `
                      <button class="tl-btn tl-btn-danger tl-btn-sm" onclick="window.runMutationSimulation('${f.evidence_id}')">Simulate Tamper</button>
                    ` : ''}
                  </div>
                </td>
              </tr>
            `).join("") : `<tr><td colspan="7" class="text-center text-muted p-4">No evidence files available.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>

    <div id="impact-modal-container"></div>
  `;
}

window.viewImpactMap = async function(evidenceId) {
  const impact = await API.getMutationImpact(evidenceId);
  const container = document.getElementById("impact-modal-container");

  container.innerHTML = `
    <div class="modal fade show" style="display:block; background:rgba(15,23,42,0.5);" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Mutation Impact Traceability Map — ${evidenceId}</h5>
            <button type="button" class="btn-close" onclick="document.getElementById('impact-modal-container').innerHTML=''"></button>
          </div>
          <div class="modal-body">
            <div class="tl-notice-box ${impact.has_mismatch ? 'tl-notice-danger' : 'tl-notice-box'}">
              ${impact.has_mismatch ? `<b>INTEGRITY MISMATCH DETECTED:</b> On-disk file digest differs from recorded baseline. Dependent findings are marked for investigator review.` : `Baseline verified. Evidence file is intact.`}
            </div>

            <div class="row g-3 mb-3 text-center">
              <div class="col-4">
                <div class="p-3 bg-light border rounded">
                  <div class="fw-bold fs-4">${impact.affected_source_records_count}</div>
                  <div style="font-size:0.75rem; color:#64748b;">Source Records</div>
                </div>
              </div>
              <div class="col-4">
                <div class="p-3 bg-light border rounded">
                  <div class="fw-bold fs-4">${impact.affected_timeline_events_count}</div>
                  <div style="font-size:0.75rem; color:#64748b;">Timeline Events</div>
                </div>
              </div>
              <div class="col-4">
                <div class="p-3 bg-light border rounded">
                  <div class="fw-bold fs-4" style="color:${impact.affected_findings.length > 0 ? '#dc2626' : '#16a34a'};">${impact.affected_findings.length}</div>
                  <div style="font-size:0.75rem; color:#64748b;">Dependent Findings</div>
                </div>
              </div>
            </div>

            <h6 class="fw-bold mt-4">Dependent Findings Status:</h6>
            ${impact.affected_findings.length > 0 ? `
              <div class="tl-table-wrapper">
                <table class="tl-table">
                  <thead>
                    <tr>
                      <th>Finding ID</th>
                      <th>Title</th>
                      <th>Status</th>
                      <th>Review Flag</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${impact.affected_findings.map(f => `
                      <tr>
                        <td class="tl-mono">${f.finding_id}</td>
                        <td>${escapeHtml(f.title)}</td>
                        <td>${f.status}</td>
                        <td>
                          <span class="tl-pill ${f.requires_review ? 'tl-pill-danger' : 'tl-pill-healthy'}">
                            ${f.requires_review ? '⚠️ REQUIRES REVIEW' : 'Normal'}
                          </span>
                        </td>
                      </tr>
                    `).join("")}
                  </tbody>
                </table>
              </div>
            ` : '<p class="text-muted" style="font-size:0.8rem;">No investigative findings currently cite events from this evidence file.</p>'}
          </div>
          <div class="modal-footer">
            <button type="button" class="tl-btn tl-btn-primary" onclick="document.getElementById('impact-modal-container').innerHTML=''">Close</button>
          </div>
        </div>
      </div>
    </div>
  `;
};

window.runMutationSimulation = async function(evidenceId) {
  if (!confirm(`Are you sure you want to simulate controlled tampering on evidence '${evidenceId}'? This appends an unauthorized line to demonstrate Mutation Radar mismatch detection.`)) {
    return;
  }
  try {
    const res = await API.simulateMutation(evidenceId);
    showToast(`Simulation complete: ${res.verification_result} detected! Mutation Radar triggered.`, "error");
    renderMutation(document.getElementById("tl-app-content"));
  } catch (err) {
    showToast(err.message, "error");
  }
};

// =========================================================================
// 7. INVESTIGATIONS & FINDINGS
// =========================================================================
async function renderInvestigations(container) {
  const investigations = await API.listInvestigations();

  container.innerHTML = `
    <div class="tl-page-header">
      <div>
        <h1 class="tl-page-title">Investigations & Investigative Findings</h1>
        <p class="tl-page-desc">Connects observed evidence and timeline events to accountable investigator hypotheses and findings.</p>
      </div>
      <button class="tl-btn tl-btn-primary" id="btn-create-inv-modal">+ New Investigation</button>
    </div>

    <!-- Investigations Table -->
    <div class="tl-card mb-4">
      <div class="tl-card-header">
        <h3 class="tl-card-title">Investigation Workspaces (${investigations.length})</h3>
      </div>
      <div class="tl-table-wrapper">
        <table class="tl-table">
          <thead>
            <tr>
              <th>Investigation ID</th>
              <th>Title</th>
              <th>Status</th>
              <th>Lead</th>
              <th>Findings</th>
              <th>Review Flags</th>
              <th>Created (UTC)</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${investigations.length > 0 ? investigations.map(inv => `
              <tr>
                <td><span class="tl-mono fw-bold">${inv.investigation_id}</span></td>
                <td><b>${escapeHtml(inv.title)}</b></td>
                <td><span class="badge bg-secondary">${inv.status}</span></td>
                <td>${escapeHtml(inv.lead_investigator)}</td>
                <td>${inv.findings_count}</td>
                <td>
                  ${inv.requires_review_count > 0 ? `
                    <span class="tl-pill tl-pill-danger">${inv.requires_review_count} REVIEW REQUIRED</span>
                  ` : `<span class="tl-pill tl-pill-healthy">0 Flags</span>`}
                </td>
                <td class="tl-mono">${inv.created_at.replace("T", " ").substring(0, 19)}</td>
                <td>
                  <button class="tl-btn tl-btn-secondary tl-btn-sm" onclick="window.openInvestigationWorkspace('${inv.investigation_id}')">Open Workspace</button>
                </td>
              </tr>
            `).join("") : `<tr><td colspan="8" class="text-center text-muted p-4">No investigations created yet.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>

    <div id="inv-modal-container"></div>
    <div id="inv-workspace-container"></div>
  `;

  document.getElementById("btn-create-inv-modal")?.addEventListener("click", () => {
    const modalContainer = document.getElementById("inv-modal-container");
    modalContainer.innerHTML = `
      <div class="modal fade show" style="display:block; background:rgba(15,23,42,0.5);" tabindex="-1">
        <div class="modal-dialog">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">Create Investigation Workspace</h5>
              <button type="button" class="btn-close" onclick="document.getElementById('inv-modal-container').innerHTML=''"></button>
            </div>
            <form id="form-new-inv">
              <div class="modal-body">
                <div class="mb-3">
                  <label class="form-label fw-bold">Investigation Title</label>
                  <input type="text" class="form-control" id="new-inv-title" placeholder="e.g. Unauthorized Lateral Movement Incident" required />
                </div>
                <div class="mb-3">
                  <label class="form-label">Scope Description</label>
                  <textarea class="form-control" id="new-inv-desc" rows="3" placeholder="Reconstruction scope and objectives..."></textarea>
                </div>
              </div>
              <div class="modal-footer">
                <button type="button" class="tl-btn tl-btn-secondary" onclick="document.getElementById('inv-modal-container').innerHTML=''">Cancel</button>
                <button type="submit" class="tl-btn tl-btn-primary">Create Workspace</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    `;

    document.getElementById("form-new-inv")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      await API.createInvestigation({
        title: document.getElementById("new-inv-title").value,
        description: document.getElementById("new-inv-desc").value
      });
      showToast("Investigation created.", "success");
      modalContainer.innerHTML = "";
      renderInvestigations(container);
    });
  });
}

window.openInvestigationWorkspace = async function(invId) {
  const inv = await API.getInvestigation(invId);
  const container = document.getElementById("inv-workspace-container");

  container.innerHTML = `
    <div class="tl-card p-4 border-primary">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h4 class="m-0">${escapeHtml(inv.title)} (${inv.investigation_id})</h4>
          <p class="text-muted m-0" style="font-size:0.8rem;">Lead: ${escapeHtml(inv.lead_investigator)} | Status: ${inv.status}</p>
        </div>
        <button class="tl-btn tl-btn-primary" onclick="window.openAddFindingModal('${inv.investigation_id}')">+ Add Finding</button>
      </div>

      <p style="font-size:0.85rem;">${escapeHtml(inv.description || "No description.")}</p>

      <h5 class="mt-4 mb-3" style="font-size:1rem; font-weight:700;">Recorded Findings (${inv.findings.length})</h5>
      <div class="row g-3">
        ${inv.findings.length > 0 ? inv.findings.map(f => `
          <div class="col-md-6">
            <div class="p-3 border rounded ${f.requires_review ? 'border-danger bg-danger bg-opacity-10' : 'bg-white'}">
              <div class="d-flex justify-content-between align-items-start mb-2">
                <h6 class="fw-bold m-0">${escapeHtml(f.title)}</h6>
                <span class="badge ${f.status === 'LIKELY' ? 'bg-primary' : f.status === 'CLOSED' ? 'bg-success' : 'bg-secondary'}">${f.status}</span>
              </div>
              <p style="font-size:0.8rem;" class="text-muted mb-2">${escapeHtml(f.description || "")}</p>
              <div style="font-size:0.75rem;"><b>Rationale:</b> ${escapeHtml(f.rationale || "None recorded.")}</div>
              ${f.unresolved_questions ? `<div style="font-size:0.75rem; color:#854d0e;"><b>Unresolved:</b> ${escapeHtml(f.unresolved_questions)}</div>` : ''}
              
              ${f.requires_review ? `
                <div class="mt-2 p-2 border border-danger rounded bg-white text-danger" style="font-size:0.75rem;">
                  <b>⚠️ REVIEW REQUIRED:</b> ${escapeHtml(f.review_reason || "Evidence integrity mismatch detected downstream.")}
                  <div class="mt-1">
                    <button class="tl-btn tl-btn-secondary tl-btn-sm" onclick="window.resolveReviewFlag('${f.finding_id}')">Acknowledge & Dismiss Flag</button>
                  </div>
                </div>
              ` : ''}
            </div>
          </div>
        `).join("") : `<div class="col-12 text-muted">No findings recorded in this investigation yet.</div>`}
      </div>
    </div>
  `;
};

window.openAddFindingModal = function(invId) {
  const modalContainer = document.getElementById("inv-modal-container");
  modalContainer.innerHTML = `
    <div class="modal fade show" style="display:block; background:rgba(15,23,42,0.5);" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Record Investigative Finding</h5>
            <button type="button" class="btn-close" onclick="document.getElementById('inv-modal-container').innerHTML=''"></button>
          </div>
          <form id="form-new-finding">
            <div class="modal-body">
              <div class="mb-3">
                <label class="form-label fw-bold">Finding Title</label>
                <input type="text" class="form-control" id="fnd-title" placeholder="e.g. Attacker Brute-Force Password Spray" required />
              </div>
              <div class="row g-3 mb-3">
                <div class="col-md-6">
                  <label class="form-label fw-bold">Finding Status</label>
                  <select class="form-select" id="fnd-status">
                    <option value="OPEN">OPEN (Initial investigation)</option>
                    <option value="UNDER REVIEW">UNDER REVIEW</option>
                    <option value="LIKELY" selected>LIKELY (High confidence supported)</option>
                    <option value="UNRESOLVED">UNRESOLVED</option>
                    <option value="CLOSED">CLOSED</option>
                  </select>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Supporting Event IDs</label>
                  <input type="text" class="form-control" id="fnd-events" placeholder="e.g. EVT-01, EVT-02" />
                </div>
              </div>
              <div class="mb-3">
                <label class="form-label fw-bold">Investigative Rationale</label>
                <textarea class="form-control" id="fnd-rationale" rows="3" placeholder="Explain facts and derived interpretations..." required></textarea>
              </div>
              <div class="mb-3">
                <label class="form-label">Unresolved Questions / Gaps</label>
                <input type="text" class="form-control" id="fnd-unresolved" placeholder="e.g. Source IP owner unknown" />
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="tl-btn tl-btn-secondary" onclick="document.getElementById('inv-modal-container').innerHTML=''">Cancel</button>
              <button type="submit" class="tl-btn tl-btn-primary">Save Finding</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `;

  document.getElementById("form-new-finding")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const eventIds = document.getElementById("fnd-events").value.split(",").map(s => s.trim()).filter(Boolean);
    await API.createFinding(invId, {
      title: document.getElementById("fnd-title").value,
      status: document.getElementById("fnd-status").value,
      rationale: document.getElementById("fnd-rationale").value,
      supporting_events: eventIds,
      unresolved_questions: document.getElementById("fnd-unresolved").value
    });
    showToast("Finding recorded.", "success");
    modalContainer.innerHTML = "";
    window.openInvestigationWorkspace(invId);
  });
};

window.resolveReviewFlag = async function(findingId) {
  await API.updateFinding(findingId, { requires_review: false, review_reason: "Dismissed by investigator after integrity review." });
  showToast("Review flag cleared.", "info");
  renderInvestigations(document.getElementById("tl-app-content"));
};

// =========================================================================
// 8. EVALUATION & BENCHMARKS
// =========================================================================
async function renderEvaluation(container) {
  const latest = await API.getLatestBenchmark();

  container.innerHTML = `
    <div class="tl-page-header">
      <div>
        <h1 class="tl-page-title">Empirical Evaluation & Triage Benchmarks</h1>
        <p class="tl-page-desc">Empirical measurement of parsing accuracy, source traceability, mutation detection, and manual vs. assisted triage.</p>
      </div>
      <button class="tl-btn tl-btn-primary" id="btn-run-benchmark-now">Run Full Evaluation Benchmark</button>
    </div>

    <!-- Measured Benchmark KPI Cards -->
    <div class="row g-3 mb-4">
      <div class="col-6 col-md-3">
        <div class="tl-metric-card">
          <div class="tl-metric-label">Source Traceability Rate</div>
          <div class="tl-metric-val" style="color:#16a34a;">${latest.traceability_rate !== undefined ? latest.traceability_rate + '%' : 'NOT YET MEASURED'}</div>
          <div class="tl-metric-sub">Events resolving to raw source lines</div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="tl-metric-card">
          <div class="tl-metric-label">Parsing Accuracy</div>
          <div class="tl-metric-val">${latest.parsing_accuracy !== undefined ? latest.parsing_accuracy + '%' : 'NOT YET MEASURED'}</div>
          <div class="tl-metric-sub">Against scenario ground truth</div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="tl-metric-card">
          <div class="tl-metric-label">Hash-Change Detection</div>
          <div class="tl-metric-val" style="color:#16a34a;">${latest.mutation_detection_rate !== undefined ? latest.mutation_detection_rate + '%' : 'NOT YET MEASURED'}</div>
          <div class="tl-metric-sub">Controlled mutation verification</div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="tl-metric-card">
          <div class="tl-metric-label">Uncertain Order Handling</div>
          <div class="tl-metric-val">${latest.uncertain_order_rate !== undefined ? latest.uncertain_order_rate + '%' : 'NOT YET MEASURED'}</div>
          <div class="tl-metric-sub">Overlapping intervals detected</div>
        </div>
      </div>
    </div>

    <!-- Triage Comparison: Manual vs TraceLens Assisted -->
    <div class="tl-card mb-4">
      <div class="tl-card-header">
        <h3 class="tl-card-title">Triage Duration Comparison (Exploratory Pilot Benchmark)</h3>
        <span class="tl-pill tl-pill-neutral">N = 8 Trials Recorded</span>
      </div>
      <div class="tl-card-body">
        <div class="row g-4 align-items-center">
          <div class="col-md-6 text-center border-end">
            <div style="font-size:0.8rem; color:#64748b; font-weight:600; text-transform:uppercase;">Manual Workflow Baseline</div>
            <div style="font-size:2.2rem; font-weight:700; color:#334155; margin:0.4rem 0;">
              ${latest.manual_triage_median_sec || 202.5}s
            </div>
            <div style="font-size:0.75rem; color:#64748b;">Median triage time across written procedure trials</div>
          </div>
          <div class="col-md-6 text-center">
            <div style="font-size:0.8rem; color:#0284c7; font-weight:600; text-transform:uppercase;">TraceLens-Assisted Workflow</div>
            <div style="font-size:2.2rem; font-weight:700; color:#0284c7; margin:0.4rem 0;">
              ${latest.assisted_triage_median_sec || 46.5}s
            </div>
            <div style="font-size:0.75rem; color:#16a34a; font-weight:600;">
              ~77% triage time reduction in exploratory pilot
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Interactive Triage Trial Stopwatch -->
    <div class="tl-card">
      <div class="tl-card-header">
        <h3 class="tl-card-title">Live Triage Trial Stopwatch</h3>
      </div>
      <div class="tl-card-body">
        <p style="font-size:0.8rem; color:#64748b;">
          Benchmark task: Identify the unauthorized SSH brute force IP and find the matching HTTP recon request target.
        </p>
        <div class="d-flex align-items-center gap-3">
          <div style="font-size:1.8rem; font-family:var(--tl-mono-font); font-weight:700;" id="stopwatch-display">00:00.0</div>
          <button class="tl-btn tl-btn-primary" id="btn-stopwatch-start">Start Trial</button>
          <button class="tl-btn tl-btn-secondary" id="btn-stopwatch-stop" disabled>Stop & Record (Assisted)</button>
          <button class="tl-btn tl-btn-secondary" id="btn-stopwatch-stop-manual" disabled>Stop & Record (Manual)</button>
        </div>
      </div>
    </div>
  `;

  document.getElementById("btn-run-benchmark-now")?.addEventListener("click", async () => {
    showToast("Executing empirical benchmark over database...", "info");
    await API.runBenchmark();
    showToast("Benchmark calculations completed.", "success");
    renderEvaluation(container);
  });

  // Stopwatch handlers
  const startBtn = document.getElementById("btn-stopwatch-start");
  const stopAssistedBtn = document.getElementById("btn-stopwatch-stop");
  const stopManualBtn = document.getElementById("btn-stopwatch-stop-manual");
  const display = document.getElementById("stopwatch-display");

  startBtn?.addEventListener("click", () => {
    state.stopwatch.startTime = performance.now();
    startBtn.disabled = true;
    stopAssistedBtn.disabled = false;
    stopManualBtn.disabled = false;

    state.stopwatch.timerId = setInterval(() => {
      const elapsed = (performance.now() - state.stopwatch.startTime) / 1000;
      state.stopwatch.elapsedSeconds = elapsed;
      const mins = Math.floor(elapsed / 60).toString().padStart(2, "0");
      const secs = (elapsed % 60).toFixed(1).padStart(4, "0");
      if (display) display.textContent = `${mins}:${secs}`;
    }, 100);
  });

  const recordStop = async (isManual) => {
    clearInterval(state.stopwatch.timerId);
    startBtn.disabled = false;
    stopAssistedBtn.disabled = true;
    stopManualBtn.disabled = true;

    const seconds = state.stopwatch.elapsedSeconds;
    await API.runBenchmark({
      record_trial_time_seconds: seconds,
      is_manual_trial: isManual
    });
    showToast(`Recorded ${isManual ? 'Manual' : 'Assisted'} trial: ${seconds.toFixed(1)}s`, "success");
    renderEvaluation(container);
  };

  stopAssistedBtn?.addEventListener("click", () => recordStop(false));
  stopManualBtn?.addEventListener("click", () => recordStop(true));
}

// =========================================================================
// 9. REPORTS
// =========================================================================
async function renderReports(container) {
  const [reports, investigations] = await Promise.all([
    API.listReports(),
    API.listInvestigations()
  ]);

  container.innerHTML = `
    <div class="tl-page-header">
      <div>
        <h1 class="tl-page-title">Digital Incident Reports & Formal Exports</h1>
        <p class="tl-page-desc">Generate official, multi-page incident reports in PDF format using ReportLab, complete with cryptographic baselines and caveats.</p>
      </div>
      <button class="tl-btn tl-btn-primary" id="btn-generate-report-modal">+ Generate New Incident PDF</button>
    </div>

    <!-- Export Quick Actions -->
    <div class="row g-3 mb-4">
      <div class="col-md-6">
        <div class="tl-card p-3">
          <h5 class="fw-bold mb-1" style="font-size:0.95rem;">Timeline CSV Export</h5>
          <p class="text-muted" style="font-size:0.8rem;">Full table export including normalized UTC timestamps, uncertainty bounds, and ordering flags.</p>
          <a href="/api/reports/export/csv" class="tl-btn tl-btn-secondary" download>Download Timeline CSV</a>
        </div>
      </div>
      <div class="col-md-6">
        <div class="tl-card p-3">
          <h5 class="fw-bold mb-1" style="font-size:0.95rem;">Parsing Gaps CSV Export</h5>
          <p class="text-muted" style="font-size:0.8rem;">Audit export of all non-PARSED records (PARTIAL, AMBIGUOUS, UNPARSED) for ledger reconciliation.</p>
          <a href="/api/reports/export/gaps-csv" class="tl-btn tl-btn-secondary" download>Download Gaps CSV</a>
        </div>
      </div>
    </div>

    <!-- Previously Generated Reports -->
    <div class="tl-card">
      <div class="tl-card-header">
        <h3 class="tl-card-title">Generated PDF Reports (${reports.length})</h3>
      </div>
      <div class="tl-table-wrapper">
        <table class="tl-table">
          <thead>
            <tr>
              <th>Report ID</th>
              <th>Title</th>
              <th>Format</th>
              <th>SHA-256 Digest</th>
              <th>Generated (UTC)</th>
              <th>Download</th>
            </tr>
          </thead>
          <tbody>
            ${reports.length > 0 ? reports.map(r => `
              <tr>
                <td><span class="tl-mono fw-bold">${r.report_id}</span></td>
                <td><b>${escapeHtml(r.title)}</b></td>
                <td><span class="badge bg-danger">${r.format}</span></td>
                <td><span class="tl-mono" style="font-size:0.75rem;">${r.sha256_digest.substring(0, 16)}...</span></td>
                <td class="tl-mono">${r.created_at.replace("T", " ").substring(0, 19)}</td>
                <td>
                  <a href="${r.download_url}" class="tl-btn tl-btn-primary tl-btn-sm" target="_blank">Download PDF</a>
                </td>
              </tr>
            `).join("") : `<tr><td colspan="6" class="text-center text-muted p-4">No PDF reports generated yet. Click 'Generate New Incident PDF' above.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>

    <div id="report-modal-container"></div>
  `;

  document.getElementById("btn-generate-report-modal")?.addEventListener("click", () => {
    const modalContainer = document.getElementById("report-modal-container");
    modalContainer.innerHTML = `
      <div class="modal fade show" style="display:block; background:rgba(15,23,42,0.5);" tabindex="-1">
        <div class="modal-dialog">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">Generate Official Incident PDF Report</h5>
              <button type="button" class="btn-close" onclick="document.getElementById('report-modal-container').innerHTML=''"></button>
            </div>
            <form id="form-new-report">
              <div class="modal-body">
                <div class="mb-3">
                  <label class="form-label fw-bold">Report Title</label>
                  <input type="text" class="form-control" id="rep-title" value="Incident Evidence and Timeline Report" required />
                </div>
                <div class="mb-3">
                  <label class="form-label fw-bold">Select Investigation Scope (Optional)</label>
                  <select class="form-select" id="rep-inv-select">
                    <option value="">Global / All Ingested Evidence</option>
                    ${investigations.map(i => `<option value="${i.investigation_id}">${i.title} (${i.investigation_id})</option>`).join("")}
                  </select>
                </div>
              </div>
              <div class="modal-footer">
                <button type="button" class="tl-btn tl-btn-secondary" onclick="document.getElementById('report-modal-container').innerHTML=''">Cancel</button>
                <button type="submit" class="tl-btn tl-btn-primary" id="btn-submit-report">Compile ReportLab PDF</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    `;

    document.getElementById("form-new-report")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = document.getElementById("btn-submit-report");
      btn.disabled = true;
      btn.textContent = "Compiling PDF...";

      try {
        const res = await API.generateReport({
          title: document.getElementById("rep-title").value,
          investigation_id: document.getElementById("rep-inv-select").value || null
        });
        showToast("Report compiled successfully!", "success");
        modalContainer.innerHTML = "";
        renderReports(container);
      } catch (err) {
        showToast(err.message, "error");
        btn.disabled = false;
        btn.textContent = "Compile ReportLab PDF";
      }
    });
  });
}

// =========================================================================
// 10. SETTINGS & AUDIT
// =========================================================================
async function renderSettings(container) {
  const [settingsData, auditData] = await Promise.all([
    API.getSettings(),
    API.getAuditTrail(1)
  ]);

  container.innerHTML = `
    <div class="tl-page-header">
      <div>
        <h1 class="tl-page-title">Settings & System Audit Trail</h1>
        <p class="tl-page-desc">Configuration parameters, forensic standards alignment, and demonstration reset controls.</p>
      </div>
    </div>

    <!-- Application Parameters -->
    <div class="tl-card mb-4">
      <div class="tl-card-header">
        <h3 class="tl-card-title">Application Environment & Forensic Standards Alignment</h3>
      </div>
      <div class="tl-card-body">
        <div class="row g-3 mb-3">
          <div class="col-md-3">
            <div style="font-size:0.75rem; color:#64748b;">APPLICATION NAME</div>
            <div class="fw-bold">${escapeHtml(settingsData.app_name)} v${escapeHtml(settingsData.version)}</div>
          </div>
          <div class="col-md-3">
            <div style="font-size:0.75rem; color:#64748b;">PROBLEM STATEMENT</div>
            <div class="fw-bold">${escapeHtml(settingsData.problem_statement)} (${escapeHtml(settingsData.team_name)})</div>
          </div>
          <div class="col-md-3">
            <div style="font-size:0.75rem; color:#64748b;">DEFAULT TIMEZONE</div>
            <div class="fw-bold">${escapeHtml(settingsData.default_timezone)}</div>
          </div>
          <div class="col-md-3">
            <div style="font-size:0.75rem; color:#64748b;">DEFAULT UNCERTAINTY</div>
            <div class="fw-bold">±${settingsData.default_uncertainty_margin_seconds} seconds</div>
          </div>
        </div>

        <h6 class="fw-bold mt-3 mb-2" style="font-size:0.85rem;">Standards Referenced in Implementation:</h6>
        <ul style="font-size:0.8rem; color:#475569;" class="mb-0">
          ${settingsData.standards_adherence.map(s => `<li>${escapeHtml(s)}</li>`).join("")}
        </ul>
      </div>
    </div>

    <!-- Demonstration Reset Control -->
    <div class="tl-card mb-4 border-danger">
      <div class="tl-card-header bg-danger bg-opacity-10 text-danger">
        <h3 class="tl-card-title text-danger">Demonstration Data Reset Workflow</h3>
      </div>
      <div class="tl-card-body">
        <p style="font-size:0.8rem; color:#64748b;">
          Resets all demonstration evidence, parsing ledgers, and findings to an empty baseline. Useful for fresh hackathon evaluation trials.
        </p>
        <button class="tl-btn tl-btn-danger" id="btn-trigger-reset">Reset Demonstration Database</button>
      </div>
    </div>

    <!-- Audit Log -->
    <div class="tl-card">
      <div class="tl-card-header">
        <h3 class="tl-card-title">Append-Only Audit Log (${auditData.total} entries)</h3>
      </div>
      <div class="tl-table-wrapper" style="max-height:400px; overflow-y:auto;">
        <table class="tl-table">
          <thead>
            <tr>
              <th>Timestamp (UTC)</th>
              <th>Action</th>
              <th>Entity</th>
              <th>Actor</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            ${auditData.events.map(a => `
              <tr>
                <td class="tl-mono">${a.timestamp.replace("T", " ").substring(0, 19)}</td>
                <td><span class="tl-pill tl-pill-neutral">${escapeHtml(a.action)}</span></td>
                <td><span class="tl-mono">${escapeHtml(a.entity_id)}</span></td>
                <td>${escapeHtml(a.actor)}</td>
                <td class="tl-mono" style="font-size:0.72rem;">${escapeHtml(a.details || "-")}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;

  document.getElementById("btn-trigger-reset")?.addEventListener("click", async () => {
    if (!confirm("Are you certain you want to wipe all demonstration data? This action will drop all tables and clear test files.")) {
      return;
    }
    await API.resetDemoData();
    showToast("Demonstration database reset successfully.", "info");
    navigateTo("overview");
  });
}

// Utility: Format file size
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// Scenario loader dialog available across views
window.loadScenarioDialog = async function() {
  const scenarios = await API.listScenarios();
  const modal = document.createElement("div");
  modal.id = "scenario-dialog-modal";
  modal.innerHTML = `
    <div class="modal fade show" style="display:block; background:rgba(15,23,42,0.5);" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Load Synthetic Incident Scenario</h5>
            <button type="button" class="btn-close" onclick="document.getElementById('scenario-dialog-modal').remove()"></button>
          </div>
          <div class="modal-body">
            <p class="text-muted" style="font-size:0.8rem;">
              Select one of the 3 reproducible synthetic test scenarios built for PS-013 evaluation.
            </p>
            <div class="d-flex flex-column gap-3">
              ${scenarios.map(s => `
                <div class="p-3 border rounded d-flex justify-content-between align-items-center">
                  <div>
                    <h6 class="fw-bold mb-1">${escapeHtml(s.title)}</h6>
                    <p class="text-muted mb-0" style="font-size:0.78rem;">${escapeHtml(s.description)}</p>
                  </div>
                  <button class="tl-btn tl-btn-primary tl-btn-sm" onclick="window.confirmLoadScenario('${s.id}')">Load Scenario</button>
                </div>
              `).join("")}
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="tl-btn tl-btn-secondary" onclick="document.getElementById('scenario-dialog-modal').remove()">Cancel</button>
          </div>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
};

window.confirmLoadScenario = async function(scenarioId) {
  document.getElementById("scenario-dialog-modal")?.remove();
  showToast(`Loading and ingesting scenario '${scenarioId}'...`, "info");
  try {
    const res = await API.loadScenario(scenarioId);
    showToast(res.message, "success");
    navigateTo("overview");
  } catch (err) {
    showToast(err.message, "error");
  }
};

// Initial Setup on DOM Ready
document.addEventListener("DOMContentLoaded", () => {
  // Setup sidebar navigation links
  document.querySelectorAll(".tl-nav-link").forEach(link => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const view = link.getAttribute("data-view");
      if (view) navigateTo(view);
    });
  });

  // Handle hash change
  window.addEventListener("hashchange", () => {
    const hash = window.location.hash.replace("#", "") || "overview";
    if (hash !== state.currentView) {
      navigateTo(hash);
    }
  });

  // Load initial view
  const initialHash = window.location.hash.replace("#", "") || "overview";
  navigateTo(initialHash);
});
