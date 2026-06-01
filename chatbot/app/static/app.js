const state = {
  patents: [],
  selectedPatentId: null,
  currentAudit: null,
};

const $ = (id) => document.getElementById(id);

function log(message, payload) {
  const at = new Date().toLocaleTimeString();
  const text = payload ? `${message}\n${JSON.stringify(payload, null, 2)}` : message;
  $("activityLog").textContent = `[${at}] ${text}\n\n${$("activityLog").textContent}`;
}

function setBusy(button, busy) {
  if (!button) return;
  button.disabled = busy;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }
  if (!response.ok) {
    const detail = data?.detail || data;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

function badgeClass(value) {
  if (value === true || value === "human_reviewed" || value === "applied" || value === "clean") return "good";
  if (value === false || value === "human_review_required") return "warn";
  return "";
}

function pill(value) {
  return `<span class="badge ${badgeClass(value)}">${value ?? "-"}</span>`;
}

function metric(label, value) {
  return `<div><span>${label}</span><strong>${value ?? "-"}</strong></div>`;
}

function renderOverview(config, vectorStatus) {
  $("dataRoot").textContent = config?.data_root?.path || config?.data_root || "-";
  $("patentCount").textContent = config?.patent_count ?? state.patents.length ?? "-";
  $("globalDocCount").textContent = vectorStatus?.global?.document_count ?? "-";
  $("vectorSource").textContent = vectorStatus?.global?.source ?? "-";
  const reviewed = (vectorStatus?.patents || []).filter((item) => item.has_human_reviewed_source).length;
  $("reviewedCount").textContent = reviewed || "-";
}

function renderPatents() {
  const list = $("patentList");
  list.innerHTML = "";
  const select = $("queryPatentSelect");
  select.innerHTML = `<option value="">All patents</option>`;

  state.patents.forEach((patent) => {
    const patentId = patent.patent_id;
    const item = document.createElement("article");
    item.className = `list-item ${patentId === state.selectedPatentId ? "active" : ""}`;
    item.innerHTML = `
      <div>
        <strong>${patentId}</strong>
        <span class="muted">${patent.title || "No title"}</span>
      </div>
      ${pill(patent.has_local_vectorstore)}
    `;
    item.addEventListener("click", () => {
      state.selectedPatentId = patentId;
      renderPatents();
      loadPatentDetail();
    });
    list.appendChild(item);

    const option = document.createElement("option");
    option.value = patentId;
    option.textContent = patentId;
    select.appendChild(option);
  });

  if (state.selectedPatentId) {
    select.value = state.selectedPatentId;
  }
}

function renderPatentDetail(detail) {
  $("selectedPatentTitle").textContent = detail?.patent_id || "Patent detail";
  $("patentDetail").innerHTML = [
    metric("latest input", detail?.has_latest_input),
    metric("latest report", detail?.has_latest_report),
    metric("latest PDF", detail?.has_latest_pdf),
    metric("chunk count", detail?.chunk_count),
    metric("local vectorstore", detail?.has_local_vectorstore),
    metric("wiki index", detail?.has_wiki_index),
    metric("report JSON files", detail?.report_json_count),
    metric("assets", detail?.asset_count),
  ].join("");
}

function renderAudit(audit) {
  state.currentAudit = audit;
  $("auditIdInput").value = audit?.audit_id || "";
  const summary = audit?.summary || {};
  $("auditSummary").innerHTML = [
    metric("audit id", audit?.audit_id),
    metric("status", audit?.status),
    metric("documents scanned", summary.documents_scanned),
    metric("findings", summary.finding_count),
    metric("default exclude", summary.default_exclude_count),
    metric("review", summary.review_count),
  ].join("");

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
                <span class="muted">${finding.message || ""}</span>
                <p class="excerpt">${finding.excerpt || ""}</p>
                <footer>
                  ${pill(finding.severity)}
                  ${pill(finding.default_action)}
                  ${pill(finding.patent_id || "_global")}
                  ${pill(finding.source_type || "unknown")}
                </footer>
              </div>
            </article>
          `;
        })
        .join("")
    : `<article class="finding"><div></div><div><strong>No findings</strong></div></article>`;
}

function renderReview(review) {
  $("reviewMarkdown").textContent = review?.markdown || "No review loaded.";
  if (review?.audit?.audit_id) {
    $("auditIdInput").value = review.audit.audit_id;
    renderAudit(review.audit);
  }
}

function renderQueryResults(result) {
  const hits = result?.hits || [];
  $("queryResults").innerHTML = `
    <article class="hit">
      <strong>${result?.mode || "query"} / ${hits.length} hits</strong>
      <span class="muted">patent: ${result?.patent_id || "all"}</span>
    </article>
    ${hits
      .map(
        (hit) => `
          <article class="hit">
            <strong>${hit.patent_id} / score ${hit.score}</strong>
            <p class="excerpt">${hit.excerpt || ""}</p>
            <footer>
              ${pill(hit.metadata?.source_type || "unknown")}
              ${pill(hit.metadata?.section_title || hit.metadata?.file_name || "source")}
            </footer>
          </article>
        `,
      )
      .join("")}
  `;
}

function selectedFindingIds() {
  return [...document.querySelectorAll(".finding-check:checked")].map((item) => item.value);
}

function selectedSourceTypes() {
  return [...document.querySelectorAll(".source-filters input:checked")].map((item) => item.value);
}

async function loadBasics() {
  const [health, config, patents, status] = await Promise.all([
    api("/health"),
    api("/api/v1/chatbot/config"),
    api("/api/v1/chatbot/patents"),
    api("/api/v1/wiki/agent/run", { method: "POST", body: JSON.stringify({ mode: "status" }) }),
  ]);
  $("serverStatus").textContent = health.status;
  state.patents = patents.items || [];
  state.selectedPatentId = state.selectedPatentId || state.patents[0]?.patent_id || null;
  renderOverview(config, status.vectorstore_status || config.vectorstore);
  renderPatents();
  if (state.selectedPatentId) {
    await loadPatentDetail();
  }
  log("Loaded console state", {
    patents: state.patents.length,
    vector_source: status.vectorstore_status?.global?.source,
  });
}

async function loadPatentDetail() {
  if (!state.selectedPatentId) return;
  const detail = await api(`/api/v1/chatbot/patents/${encodeURIComponent(state.selectedPatentId)}?include_files=false`);
  renderPatentDetail(detail);
}

async function refreshStatus() {
  const result = await api("/api/v1/wiki/agent/run", { method: "POST", body: JSON.stringify({ mode: "status" }) });
  renderOverview({ patent_count: state.patents.length, data_root: $("dataRoot").textContent }, result.vectorstore_status);
  log("Vectorstore status", result.vectorstore_status?.global);
}

async function runAudit() {
  const button = $("runAuditButton");
  setBusy(button, true);
  try {
    const audit = await api("/api/v1/wiki/audit", { method: "POST" });
    renderAudit(audit);
    log("Audit completed", audit.summary);
  } finally {
    setBusy(button, false);
  }
}

async function loadReview() {
  const auditId = $("auditIdInput").value.trim();
  const suffix = auditId ? `?audit_id=${encodeURIComponent(auditId)}` : "";
  const review = await api(`/api/v1/wiki/audit-review${suffix}`);
  renderReview(review);
  log("Review loaded", { audit_id: review?.audit?.audit_id, path: review?.path });
}

async function applyAudit() {
  const button = $("applyAuditButton");
  setBusy(button, true);
  try {
    const body = {
      audit_id: $("auditIdInput").value.trim() || null,
      exclude_finding_ids: selectedFindingIds(),
      reviewer: $("reviewerInput").value.trim() || null,
      notes: $("notesInput").value.trim() || null,
      refresh_vectorstore: true,
    };
    const result = await api("/api/v1/wiki/audit-apply", { method: "POST", body: JSON.stringify(body) });
    log("Audit applied", {
      audit_id: result.audit_id,
      excluded: result.excluded_finding_ids?.length,
      approved: result.approved?.approved_document_count,
      vectorstore: result.vectorstore_refresh?.source,
    });
    await refreshStatus();
  } finally {
    setBusy(button, false);
  }
}

async function refreshVectorstore() {
  const button = $("refreshVectorButton");
  setBusy(button, true);
  try {
    const result = await api("/api/v1/chatbot/vectorstore/refresh", { method: "POST" });
    log("Vectorstore refreshed", {
      source: result.source,
      patents: result.patent_count,
      global_documents: result.global_vectorstore?.document_count,
    });
    await refreshStatus();
  } finally {
    setBusy(button, false);
  }
}

async function sendQuery() {
  const button = $("sendQueryButton");
  setBusy(button, true);
  try {
    const sourceTypes = selectedSourceTypes();
    const body = {
      query: $("queryInput").value.trim(),
      patent_id: $("queryPatentSelect").value || null,
      source_types: sourceTypes.length ? sourceTypes : null,
      top_k: Number($("topKInput").value || 5),
    };
    const result = await api("/api/v1/chatbot/query", { method: "POST", body: JSON.stringify(body) });
    renderQueryResults(result);
    log("Query completed", { mode: result.mode, hits: result.hit_count });
  } finally {
    setBusy(button, false);
  }
}

async function loadGraph() {
  const graph = await api("/api/v1/wiki/agent/mermaid");
  $("graphBox").textContent = graph.diagram || "No graph loaded.";
}

function selectDefaultFindings() {
  document.querySelectorAll(".finding-check").forEach((input) => {
    const article = input.closest(".finding");
    input.checked = article?.textContent.includes("exclude") || false;
  });
}

function bindEvents() {
  $("reloadAllButton").addEventListener("click", () => loadBasics().catch((error) => log("Reload failed", error.message)));
  $("refreshStatusButton").addEventListener("click", () => refreshStatus().catch((error) => log("Status failed", error.message)));
  $("loadPatentsButton").addEventListener("click", () => loadBasics().catch((error) => log("Load failed", error.message)));
  $("loadPatentButton").addEventListener("click", () => loadPatentDetail().catch((error) => log("Detail failed", error.message)));
  $("runAuditButton").addEventListener("click", () => runAudit().catch((error) => log("Audit failed", error.message)));
  $("loadReviewButton").addEventListener("click", () => loadReview().catch((error) => log("Review failed", error.message)));
  $("applyAuditButton").addEventListener("click", () => applyAudit().catch((error) => log("Apply failed", error.message)));
  $("selectDefaultsButton").addEventListener("click", selectDefaultFindings);
  $("sendQueryButton").addEventListener("click", () => sendQuery().catch((error) => log("Query failed", error.message)));
  $("loadGraphButton").addEventListener("click", () => loadGraph().catch((error) => log("Graph failed", error.message)));
  $("refreshVectorButton").addEventListener("click", () => refreshVectorstore().catch((error) => log("Refresh failed", error.message)));
  $("clearLogButton").addEventListener("click", () => {
    $("activityLog").textContent = "";
  });
  $("queryPatentSelect").addEventListener("change", (event) => {
    state.selectedPatentId = event.target.value || state.selectedPatentId;
  });
}

bindEvents();
loadBasics().catch((error) => {
  $("serverStatus").textContent = "error";
  log("Console failed", error.message);
});
