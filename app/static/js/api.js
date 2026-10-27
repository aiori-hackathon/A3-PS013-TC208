/**
 * TraceLens Frontend API Client
 * Interfaces with FastAPI endpoints deterministically
 */

export const API = {
  // Health & Dashboard
  async getHealth() {
    const res = await fetch("/api/health");
    return res.json();
  },

  async getDashboardSummary() {
    const res = await fetch("/api/dashboard/summary");
    return res.json();
  },

  async getRecentActivity() {
    const res = await fetch("/api/dashboard/activity");
    return res.json();
  },

  // Evidence Vault
  async listEvidence() {
    const res = await fetch("/api/evidence");
    return res.json();
  },

  async getEvidence(evidenceId) {
    const res = await fetch(`/api/evidence/${evidenceId}`);
    return res.json();
  },

  async uploadEvidence(formData) {
    const res = await fetch("/api/evidence/upload", {
      method: "POST",
      body: formData
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Upload failed");
    }
    return res.json();
  },

  async verifyEvidence(evidenceId) {
    const res = await fetch(`/api/evidence/${evidenceId}/verify`, { method: "POST" });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Verification failed");
    }
    return res.json();
  },

  async getVerificationHistory(evidenceId) {
    const res = await fetch(`/api/evidence/${evidenceId}/verification-history`);
    return res.json();
  },

  // Ingestion & Parsing
  async listIngestions() {
    const res = await fetch("/api/ingestions");
    return res.json();
  },

  async triggerIngestion(payload) {
    const res = await fetch("/api/ingestions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Ingestion failed");
    }
    return res.json();
  },

  async getLedger(ingestionId) {
    const res = await fetch(`/api/ingestions/${ingestionId}/ledger`);
    return res.json();
  },

  async inspectGaps(params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`/api/ingestions/gaps/inspect?${query}`);
    return res.json();
  },

  // Timeline
  async queryTimeline(params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`/api/events?${query}`);
    return res.json();
  },

  async getEventSource(eventId) {
    const res = await fetch(`/api/events/${eventId}/source`);
    if (!res.ok) throw new Error("Source record not found");
    return res.json();
  },

  async getRelatedEvents(eventId) {
    const res = await fetch(`/api/events/${eventId}/related`);
    return res.json();
  },

  // Clock Skew
  async listSkewEstimates() {
    const res = await fetch("/api/clock-skew");
    return res.json();
  },

  async estimateClockSkew(payload) {
    const res = await fetch("/api/clock-skew/estimate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Clock skew estimation failed");
    }
    return res.json();
  },

  // Investigations & Findings
  async listInvestigations() {
    const res = await fetch("/api/investigations");
    return res.json();
  },

  async getInvestigation(invId) {
    const res = await fetch(`/api/investigations/${invId}`);
    return res.json();
  },

  async createInvestigation(payload) {
    const res = await fetch("/api/investigations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return res.json();
  },

  async createFinding(invId, payload) {
    const res = await fetch(`/api/investigations/${invId}/findings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return res.json();
  },

  async updateFinding(findingId, payload) {
    const res = await fetch(`/api/investigations/findings/${findingId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return res.json();
  },

  // BlindLens Staged Review
  async listBlindLensReviews() {
    const res = await fetch("/api/blindlens/reviews");
    return res.json();
  },

  async getBlindLensReview(reviewId) {
    const res = await fetch(`/api/blindlens/reviews/${reviewId}`);
    return res.json();
  },

  async createBlindLensReview(payload) {
    const res = await fetch("/api/blindlens/reviews", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Review creation failed");
    }
    return res.json();
  },

  async revealContext(reviewId) {
    const res = await fetch(`/api/blindlens/reviews/${reviewId}/reveal`, { method: "POST" });
    return res.json();
  },

  async submitRevision(reviewId, payload) {
    const res = await fetch(`/api/blindlens/reviews/${reviewId}/revision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Revision submission failed");
    }
    return res.json();
  },

  async verifyBlindLensReview(reviewId) {
    const res = await fetch(`/api/blindlens/reviews/${reviewId}/verify`, { method: "POST" });
    return res.json();
  },

  // Mutation Radar
  async getMutationSummary() {
    const res = await fetch("/api/mutation/summary");
    return res.json();
  },

  async getMutationImpact(evidenceId) {
    const res = await fetch(`/api/mutation/impact/${evidenceId}`);
    return res.json();
  },

  async simulateMutation(evidenceId) {
    const res = await fetch(`/api/mutation/simulate/${evidenceId}`, { method: "POST" });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Simulation failed");
    }
    return res.json();
  },

  // Scenarios
  async listScenarios() {
    const res = await fetch("/api/scenarios");
    return res.json();
  },

  async loadScenario(scenarioId) {
    const res = await fetch(`/api/scenarios/${scenarioId}/load`, { method: "POST" });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to load scenario");
    }
    return res.json();
  },

  // Evaluation & Benchmarks
  async getLatestBenchmark() {
    const res = await fetch("/api/evaluation/latest");
    return res.json();
  },

  async runBenchmark(payload = {}) {
    const res = await fetch("/api/evaluation/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return res.json();
  },

  // Reports
  async listReports() {
    const res = await fetch("/api/reports");
    return res.json();
  },

  async generateReport(payload) {
    const res = await fetch("/api/reports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Report generation failed");
    }
    return res.json();
  },

  // Settings & Audit
  async getSettings() {
    const res = await fetch("/api/settings");
    return res.json();
  },

  async getAuditTrail(page = 1) {
    const res = await fetch(`/api/settings/audit?page=${page}`);
    return res.json();
  },

  async resetDemoData() {
    const res = await fetch("/api/settings/reset-demo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirm_reset: true })
    });
    return res.json();
  }
};
