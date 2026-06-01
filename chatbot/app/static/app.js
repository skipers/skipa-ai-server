const state = {
  patents: [],
  audit: null,
};

const $ = (id) => document.getElementById(id);

function message(text) {
  $("message").textContent = text;
}

function setBusy(button, busy) {
  button.disabled = busy;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }
  if (!response.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || data));
  }
  return data;
}

function pill(text, kind = "") {
  return `<span class="pill ${kind}">${text ?? "-"}</span>`;
}

function severityKind(value) {
  if (value === "high") return "bad";
  if (value === "medium") return "warn";
  if (value === "low") return "ok";
  return "";
}

function renderStatus(config, status) {
  $("serverStatus").textContent = "ok";
  $("dataRoot").textContent = config?.data_root?.path || "-";
  $("patentCount").textContent = config?.patent_count ?? state.patents.length;
  $("vectorSource").textContent = status?.global?.source || "-";
  $("globalDocCount").textContent = status?.global?.document_count ?? "-";
}

function renderPatentSelect() {
  const select = $("queryPatentSelect");
  select.innerHTML = `<option value="">All patents</option>`;
  state.patents.forEach((patent) => {
    const option = document.createElement("option");
    option.value = patent.patent_id;
    option.textContent = patent.patent_id;
    select.appendChild(option);
  });
  if (state.patents[0]) {
    select.value = state.patents[0].patent_id;
  }
}

function renderAudit(audit) {
  state.audit = audit;
  $("auditIdInput").value = audit?.audit_id || "";
  const summary = audit?.summary || {};
  $("auditSummary").textContent =
    `audit ${audit?.audit_id || "-"} | findings ${summary.finding_count ?? 0} | exclude ${summary.default_exclude_count ?? 0}`;

  const findings = audit?.findings || [];
  $("findingList").innerHTML = findings.length
    ? findings
        .map((finding) => {
          const checked = finding.default_action === "exclude" ? "checked" : "";
          return `
            <article class="finding">
              <input type="checkbox" class="finding-check" value="${finding.finding_id}" ${checked} />
              <div>
                <strong>${finding.finding_id} / ${finding.rule_id}</strong>
                <p>${finding.message || ""}</p>
                <div class="meta">
                  ${pill(finding.severity, severityKind(finding.severity))}
                  ${pill(finding.default_action)}
                  ${pill(finding.patent_id || "_global")}
                  ${pill(finding.source_type || "unknown")}
                </div>
              </div>
            </article>
          `;
        })
        .join("")
    : `<div class="empty">No findings.</div>`;
}

function renderReview(review) {
  $("reviewMarkdown").textContent = review?.markdown || "No review loaded.";
  if (review?.audit) {
    renderAudit(review.audit);
  }
}

function selectedFindingIds() {
  return [...document.querySelectorAll(".finding-check:checked")].map((input) => input.value);
}

function renderResults(result) {
  const hits = result?.hits || [];
  $("querySummary").textContent = `${result?.mode || "query"} | ${hits.length} hits`;
  $("queryResults").innerHTML = hits.length
    ? hits
        .map(
          (hit) => `
            <article class="hit">
              <strong>${hit.patent_id} / score ${hit.score}</strong>
              <p>${hit.excerpt || ""}</p>
              <div class="meta">
                ${pill(hit.metadata?.source_type || "unknown")}
                ${pill(hit.metadata?.section_title || hit.metadata?.file_name || "source")}
              </div>
            </article>
          `,
        )
        .join("")
    : `<div class="empty">No hits.</div>`;
}

async function loadAll() {
  message("Loading");
  const [config, patents, status] = await Promise.all([
    api("/api/v1/chatbot/config"),
    api("/api/v1/chatbot/patents"),
    api("/api/v1/wiki/agent/run", { method: "POST", body: JSON.stringify({ mode: "status" }) }),
  ]);
  state.patents = patents.items || [];
  renderStatus(config, status.vectorstore_status || config.vectorstore);
  renderPatentSelect();
  message("Ready");
}

async function runAudit() {
  const button = $("runAuditButton");
  setBusy(button, true);
  message("Running audit");
  try {
    const audit = await api("/api/v1/wiki/audit", { method: "POST" });
    renderAudit(audit);
    message("Audit loaded");
  } finally {
    setBusy(button, false);
  }
}

async function loadReview() {
  message("Loading review");
  const auditId = $("auditIdInput").value.trim();
  const suffix = auditId ? `?audit_id=${encodeURIComponent(auditId)}` : "";
  const review = await api(`/api/v1/wiki/audit-review${suffix}`);
  renderReview(review);
  message("Review loaded");
}

async function applyAudit() {
  const button = $("applyAuditButton");
  setBusy(button, true);
  message("Applying review");
  try {
    const result = await api("/api/v1/wiki/audit-apply", {
      method: "POST",
      body: JSON.stringify({
        audit_id: $("auditIdInput").value.trim() || null,
        exclude_finding_ids: selectedFindingIds(),
        reviewer: $("reviewerInput").value.trim() || null,
        notes: "simple-ui",
        refresh_vectorstore: true,
      }),
    });
    $("auditSummary").textContent =
      `applied ${result.audit_id} | excluded ${result.excluded_finding_ids?.length ?? 0} | approved ${result.approved?.approved_document_count ?? 0}`;
    await loadAll();
    message("Applied");
  } finally {
    setBusy(button, false);
  }
}

async function sendQuery() {
  const button = $("sendQueryButton");
  setBusy(button, true);
  message("Searching");
  try {
    const result = await api("/api/v1/chatbot/query", {
      method: "POST",
      body: JSON.stringify({
        query: $("queryInput").value.trim(),
        patent_id: $("queryPatentSelect").value || null,
        source_types: null,
        top_k: 5,
      }),
    });
    renderResults(result);
    message("Query complete");
  } finally {
    setBusy(button, false);
  }
}

function bind() {
  $("reloadButton").addEventListener("click", () => loadAll().catch((error) => message(error.message)));
  $("runAuditButton").addEventListener("click", () => runAudit().catch((error) => message(error.message)));
  $("loadReviewButton").addEventListener("click", () => loadReview().catch((error) => message(error.message)));
  $("applyAuditButton").addEventListener("click", () => applyAudit().catch((error) => message(error.message)));
  $("sendQueryButton").addEventListener("click", () => sendQuery().catch((error) => message(error.message)));
}

bind();
loadAll().catch((error) => message(error.message));
