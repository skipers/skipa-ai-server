const state = {
  patents: [],
  cards: [],
  audit: null,
  mermaid: "",
};

const $ = (id) => document.getElementById(id);

const workflowText = {
  audit: "LangGraph wiki audit agent가 특허 원문, 보고서 JSON, chunk, wiki 데이터를 스캔해서 EMPTY/OCR_NOISE/SECRET/DUPLICATE 같은 나쁜 데이터 후보를 찾습니다.",
  review: "감사 결과는 audit.json과 review.md로 저장됩니다. 사람은 finding별 excerpt와 metadata를 보고 제외할 항목을 확정합니다.",
  apply: "선택한 finding_id에 연결된 문서만 제외하고 나머지를 approved_context.md와 approved_documents.jsonl로 저장합니다.",
  vectorstore: "승인된 approved_documents.jsonl을 기준으로 local vectorstore를 다시 만들고, 필요하면 rag.zip FAISS/BM25 인덱스도 전처리 agent로 재생성합니다.",
  query: "질문이 들어오면 가벼운 의도 판단 뒤 복구된 FAISS+BM25+RRF RAG, 특허 원문, 보고서, wiki/승인 데이터, 웹 근거를 조합해 답변합니다.",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function setStatus(text) {
  $("statusLine").textContent = text;
}

function setBusy(button, busy, busyText = null) {
  if (!button) return;
  if (!button.dataset.label) button.dataset.label = button.textContent;
  button.disabled = busy;
  button.textContent = busy && busyText ? busyText : button.dataset.label;
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

function chip(value, kind = "") {
  return `<span class="chip ${escapeHtml(kind || String(value).toLowerCase())}">${escapeHtml(value ?? "-")}</span>`;
}

function renderAnswerHtml(text) {
  const lines = String(text || "").split("\n");
  const html = [];
  let inList = false;
  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      if (inList) {
        html.push("</ol>");
        inList = false;
      }
      return;
    }
    if (trimmed.startsWith("## ")) {
      if (inList) {
        html.push("</ol>");
        inList = false;
      }
      html.push(`<h2>${escapeHtml(trimmed.slice(3))}</h2>`);
      return;
    }
    if (/^\d+\.\s+/.test(trimmed)) {
      if (!inList) {
        html.push("<ol>");
        inList = true;
      }
      html.push(`<li>${escapeHtml(trimmed.replace(/^\d+\.\s+/, ""))}</li>`);
      return;
    }
    if (inList) {
      html.push("</ol>");
      inList = false;
    }
    html.push(`<p>${escapeHtml(line)}</p>`);
  });
  if (inList) html.push("</ol>");
  return html.join("");
}

function appendMessage(text, className, rich = false) {
  const message = document.createElement("div");
  message.className = `message ${className}`;
  if (rich) {
    message.innerHTML = renderAnswerHtml(text);
  } else {
    message.textContent = text;
  }
  $("messages").appendChild(message);
  $("messages").scrollTop = $("messages").scrollHeight;
  return message;
}

function showModal(title, bodyHtml) {
  $("modalTitle").textContent = title;
  $("modalBody").innerHTML = bodyHtml;
  $("detailModal").classList.add("open");
}

function jsonBlock(value) {
  return `<pre>${escapeHtml(JSON.stringify(value || {}, null, 2))}</pre>`;
}

function detailList(items) {
  return `<dl>${items.map(([key, value]) => `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value ?? "-")}</dd>`).join("")}</dl>`;
}

function renderPatentOptions() {
  const select = $("patentSelect");
  select.innerHTML = `<option value="__all__">전체 특허</option>`;
  state.patents.forEach((patent) => {
    const option = document.createElement("option");
    option.value = patent.patent_id;
    option.textContent = `${patent.patent_id} · ${patent.title || patent.patent_id}`;
    select.appendChild(option);
  });
  if (state.patents[0]) select.value = state.patents[0].patent_id;
}

function showTab(tabId) {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabId);
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === tabId);
  });
}

function renderDataCards() {
  const grid = $("dataGrid");
  if (!grid) return;
  grid.innerHTML = "";
  if (!state.patents.length) {
    grid.innerHTML = `<div class="empty">표시할 특허 데이터가 없습니다.</div>`;
    return;
  }
  $("dataSummary").textContent = `특허 ${state.patents.length}개 · 요약 카드 ${state.cards.length}개`;
  state.patents.forEach((patent) => {
    const card = state.cards.find((item) => item.patent_id === patent.patent_id) || {};
    const article = document.createElement("article");
    article.className = "data-card";
    article.innerHTML = `
      <h3>${escapeHtml(patent.patent_id)} · ${escapeHtml(patent.title || patent.patent_id)}</h3>
      <p>chunk ${escapeHtml(patent.chunk_count ?? 0)}개 · asset ${escapeHtml(patent.asset_count ?? 0)}개 · score ${escapeHtml(card.total || card.score_level || "-")}</p>
      <div class="chip-row">
        ${chip(patent.has_latest_input ? "원문 JSON" : "원문 없음", patent.has_latest_input ? "approved" : "review")}
        ${chip(patent.has_latest_report ? "보고서 JSON" : "보고서 없음", patent.has_latest_report ? "approved" : "review")}
        ${chip(patent.has_patent_index ? "FAISS" : "FAISS 없음", patent.has_patent_index ? "approved" : "review")}
        ${chip(patent.has_local_vectorstore ? "승인 vectorstore" : "local 없음", patent.has_local_vectorstore ? "approved" : "review")}
      </div>
      <div class="data-actions">
        <button type="button" data-action="detail">상세</button>
        <button type="button" data-action="chunks">Chunk</button>
        <a href="/files/patents/${encodeURIComponent(patent.patent_id)}/" target="_blank" rel="noreferrer">파일</a>
      </div>
    `;
    article.querySelector('[data-action="detail"]').addEventListener("click", async () => {
      const detail = await api(`/api/v1/chatbot/patents/${encodeURIComponent(patent.patent_id)}`);
      showModal(`${patent.patent_id} 데이터`, jsonBlock(detail));
    });
    article.querySelector('[data-action="chunks"]').addEventListener("click", async () => {
      const chunks = await api(`/api/v1/chatbot/patents/${encodeURIComponent(patent.patent_id)}/chunks?limit=5`);
      showModal(`${patent.patent_id} chunks`, jsonBlock(chunks));
    });
    grid.appendChild(article);
  });
}

function renderAudit(audit) {
  state.audit = audit;
  $("auditIdInput").value = audit?.audit_id || "";
  const summary = audit?.summary || {};
  $("auditSummary").textContent =
    `Audit ${audit?.audit_id || "-"} · 문서 ${summary.documents_scanned ?? 0}개 · 후보 ${summary.finding_count ?? 0}개 · 기본 제외 ${summary.default_exclude_count ?? 0}개`;

  const findings = audit?.findings || [];
  const list = $("findingList");
  list.innerHTML = "";
  if (!findings.length) {
    list.innerHTML = `<div class="empty">발견된 후보가 없습니다.</div>`;
    return;
  }
  findings.forEach((finding) => {
    const row = document.createElement("article");
    row.className = "finding";
    const checked = finding.default_action === "exclude" ? "checked" : "";
    row.innerHTML = `
      <input type="checkbox" class="finding-check" value="${escapeHtml(finding.finding_id)}" ${checked} />
      <button type="button">
        <strong>${escapeHtml(finding.finding_id)} / ${escapeHtml(finding.rule_id)}</strong>
        <p>${escapeHtml(finding.message || "")}</p>
        <div class="chip-row">
          ${chip(finding.severity)}
          ${chip(finding.default_action)}
          ${chip(finding.patent_id || "_global")}
          ${chip(finding.source_type || "unknown")}
        </div>
      </button>
    `;
    row.querySelector("button").addEventListener("click", () => {
      showModal(
        `Finding ${finding.finding_id}`,
        `${detailList([
          ["rule_id", finding.rule_id],
          ["severity", finding.severity],
          ["default_action", finding.default_action],
          ["patent_id", finding.patent_id],
          ["source_type", finding.source_type],
          ["source_path", finding.relative_source_path || finding.source_path],
          ["line", finding.line_no],
          ["message", finding.message],
        ])}<h2>Excerpt</h2><pre>${escapeHtml(finding.excerpt || "")}</pre><h2>Raw JSON</h2>${jsonBlock(finding)}`,
      );
    });
    list.appendChild(row);
  });
}

function selectedFindingIds() {
  return [...document.querySelectorAll(".finding-check:checked")].map((input) => input.value);
}

function appendAnswerMeta(metrics, sourceCards) {
  const meta = document.createElement("div");
  meta.className = "answer-meta";
  meta.innerHTML = [
    `engine ${metrics?.engine || metrics?.mode || "-"}`,
    `scope ${metrics?.scope || "-"}`,
    `mode ${metrics?.answer_mode || metrics?.mode || "-"}`,
    `근거 ${(sourceCards || []).length}개`,
    `confidence ${metrics?.confidence_score ?? metrics?.hit_count ?? "-"}`,
  ].map((item) => `<span>${escapeHtml(item)}</span>`).join("");
  $("messages").appendChild(meta);
}

function appendSources(sourceCards) {
  if (!sourceCards || sourceCards.length === 0) return;
  const details = document.createElement("details");
  details.className = "source-details";
  details.open = true;
  details.innerHTML = `<summary>근거 자료 ${sourceCards.length}개</summary>`;
  const list = document.createElement("div");
  list.className = "source-list";
  sourceCards.forEach((source) => {
    const card = document.createElement("article");
    card.className = "source-card";
    card.innerHTML = `
      <strong>${escapeHtml(source.label)} · ${escapeHtml(source.title || source.source_type)}</strong>
      <div class="chip-row">
        ${chip(source.source_type)}
        ${chip(source.page_no ? `p.${source.page_no}` : "page -")}
      </div>
      <p>${escapeHtml(source.snippet || "")}</p>
      <div class="source-actions">
        <button type="button">상세</button>
        ${source.url ? `<a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">파일</a>` : ""}
      </div>
    `;
    card.querySelector("button").addEventListener("click", () => {
      showModal(
        source.label,
        `${detailList([
          ["title", source.title],
          ["source_type", source.source_type],
          ["page_no", source.page_no],
          ["url", source.url],
        ])}<h2>Snippet</h2><pre>${escapeHtml(source.snippet || "")}</pre><h2>Metadata</h2>${jsonBlock(source.metadata)}`,
      );
    });
    list.appendChild(card);
  });
  details.appendChild(list);
  $("messages").appendChild(details);
  $("messages").scrollTop = $("messages").scrollHeight;
}

async function loadBaseData() {
  setStatus("불러오는 중");
  const [config, patents, status] = await Promise.all([
    api("/api/v1/chatbot/config"),
    api("/api/v1/chatbot/patents"),
    api("/api/v1/wiki/agent/run", { method: "POST", body: JSON.stringify({ mode: "status" }) }),
  ]);
  state.patents = patents.items || [];
  renderPatentOptions();
  renderDataCards();
  const vector = status.vectorstore_status || config.vectorstore || {};
  const engine = config.legacy_rag_engine?.available ? "legacy RAG" : "fallback";
  setStatus(`특허 ${config.patent_count ?? state.patents.length}개 · 문서 ${vector.global?.document_count ?? "-"}개 · ${engine}`);
  api("/api/v1/rag/patent-summary-cards")
    .then((cards) => {
      state.cards = cards.items || [];
      renderDataCards();
    })
    .catch(() => {
      state.cards = [];
    });
}

async function runAudit() {
  const button = $("runAuditButton");
  setBusy(button, true, "실행 중");
  try {
    const audit = await api("/api/v1/wiki/audit", { method: "POST" });
    renderAudit(audit);
    setStatus(`감사 완료 · 후보 ${audit.summary?.finding_count ?? 0}개`);
  } finally {
    setBusy(button, false);
  }
}

async function loadReview() {
  const auditId = $("auditIdInput").value.trim();
  const suffix = auditId ? `?audit_id=${encodeURIComponent(auditId)}` : "";
  const review = await api(`/api/v1/wiki/audit-review${suffix}`);
  $("reviewMarkdown").textContent = review.markdown || "";
  if (review.audit) renderAudit(review.audit);
  setStatus("검토서 로드 완료");
}

async function applyAudit() {
  const button = $("applyAuditButton");
  setBusy(button, true, "적용 중");
  try {
    const result = await api("/api/v1/wiki/audit-apply", {
      method: "POST",
      body: JSON.stringify({
        audit_id: $("auditIdInput").value.trim() || null,
        exclude_finding_ids: selectedFindingIds(),
        reviewer: $("reviewerInput").value.trim() || null,
        notes: "browser-ui",
        refresh_vectorstore: true,
      }),
    });
    setStatus(`적용 완료 · 제외 ${result.excluded_finding_ids?.length ?? 0}개 · 승인 ${result.approved?.approved_document_count ?? 0}개`);
    appendMessage(
      `감사 결과를 적용했습니다.\n제외 finding: ${result.excluded_finding_ids?.length ?? 0}개\n승인 문서: ${result.approved?.approved_document_count ?? 0}개\nvectorstore source: ${result.vectorstore_refresh?.source || "-"}`,
      "assistant",
    );
  } finally {
    setBusy(button, false);
  }
}

async function loadWorkflow() {
  const graph = await api("/api/v1/wiki/agent/mermaid");
  state.mermaid = graph.diagram || "";
  $("workflowMermaid").textContent = state.mermaid || "그래프가 없습니다.";
  setStatus("워크플로우 그래프 로드 완료");
}

async function loadIngestionWorkflow() {
  const graph = await api("/api/v1/rag/ingestion/mermaid");
  state.mermaid = graph.diagram || "";
  $("workflowMermaid").textContent = state.mermaid || "그래프가 없습니다.";
  setStatus("전처리 그래프 로드 완료");
}

async function reindexSelected() {
  const selected = $("patentSelect").value;
  if (selected === "__all__") {
    setStatus("특허를 하나 선택해 주세요");
    return;
  }
  const button = $("reindexButton");
  setBusy(button, true, "재색인 중");
  try {
    const result = await api("/api/v1/rag/reindex", {
      method: "POST",
      body: JSON.stringify({ patent_id: selected, force_rebuild: false, refresh_reviewed_vectorstore: false }),
    });
    setStatus(`재색인 완료 · ${result.scope || "PATENT"} · ${result.engine || "-"}`);
    showModal("재색인 결과", jsonBlock(result));
  } finally {
    setBusy(button, false);
  }
}

async function checkGlobalIndex() {
  const button = $("globalReindexButton");
  setBusy(button, true, "확인 중");
  try {
    const result = await api("/api/v1/rag/global/reindex", {
      method: "POST",
      body: JSON.stringify({ force_rebuild: false, refresh_reviewed_vectorstore: false }),
    });
    setStatus(`전체 인덱스 확인 완료 · ${result.engine || "-"}`);
    showModal("전체 인덱스 결과", jsonBlock(result));
  } finally {
    setBusy(button, false);
  }
}

async function ask() {
  const text = $("question").value.trim();
  if (!text) return;
  appendMessage(text, "user");
  $("question").value = "";
  const button = $("sendButton");
  setBusy(button, true, "생성 중");
  const pending = appendMessage("검색 중입니다. 승인된 vectorstore에서 근거를 찾고 답변을 구성합니다.", "assistant");
  try {
    const selected = $("patentSelect").value;
    const path = selected === "__all__" ? "/api/v1/rag/global/chat" : "/api/v1/rag/chat";
    const data = await api(path, {
      method: "POST",
      body: JSON.stringify({
        question: text,
        patent_id: selected === "__all__" ? null : selected,
        user_id: "browser-ui",
        chat_history: [],
      }),
    });
    pending.innerHTML = renderAnswerHtml(data.answer || "");
    appendAnswerMeta(data.metrics || {}, data.source_cards || []);
    appendSources(data.source_cards || []);
    setStatus(`답변 완료 · 근거 ${(data.source_cards || []).length}개`);
  } catch (error) {
    pending.textContent = `요청 실패: ${error.message}`;
  } finally {
    setBusy(button, false);
    $("question").focus();
  }
}

function bindEvents() {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => showTab(button.dataset.tab));
  });
  $("reloadButton").addEventListener("click", () => loadBaseData().catch((error) => setStatus(error.message)));
  $("loadDataButton").addEventListener("click", () => loadBaseData().catch((error) => setStatus(error.message)));
  $("reindexButton").addEventListener("click", () => reindexSelected().catch((error) => setStatus(error.message)));
  $("globalReindexButton").addEventListener("click", () => checkGlobalIndex().catch((error) => setStatus(error.message)));
  $("runAuditButton").addEventListener("click", () => runAudit().catch((error) => setStatus(error.message)));
  $("loadReviewButton").addEventListener("click", () => loadReview().catch((error) => setStatus(error.message)));
  $("applyAuditButton").addEventListener("click", () => applyAudit().catch((error) => setStatus(error.message)));
  $("loadWorkflowButton").addEventListener("click", () => loadWorkflow().catch((error) => setStatus(error.message)));
  $("loadIngestionWorkflowButton").addEventListener("click", () => loadIngestionWorkflow().catch((error) => setStatus(error.message)));
  $("sendButton").addEventListener("click", ask);
  $("question").addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
    event.preventDefault();
    ask();
  });
  document.querySelectorAll("[data-flow]").forEach((button) => {
    button.addEventListener("click", () => {
      $("workflowDetail").textContent = workflowText[button.dataset.flow] || "";
    });
  });
  $("closeModalButton").addEventListener("click", () => $("detailModal").classList.remove("open"));
  $("detailModal").addEventListener("click", (event) => {
    if (event.target.id === "detailModal") $("detailModal").classList.remove("open");
  });
}

bindEvents();
loadBaseData().catch((error) => setStatus(error.message));
