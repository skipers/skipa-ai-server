const state = {
  patents: [],
  cards: [],
  audit: null,
  mermaid: "",
  chatHistory: [],
  applicationHistory: [],
  applicationCases: [],
};

const $ = (id) => document.getElementById(id);

const workflowText = {
  audit: "LangGraph wiki audit agent가 특허 원문, 보고서 JSON, chunk, wiki 데이터를 스캔해서 EMPTY/OCR_NOISE/SECRET/DUPLICATE 같은 나쁜 데이터 후보를 찾습니다.",
  review: "감사 결과는 audit.json과 review.md로 저장됩니다. 사람은 finding별 excerpt와 metadata를 보고 제외할 항목을 확정합니다.",
  apply: "선택한 finding_id에 연결된 문서만 제외하고 나머지를 approved_context.md와 approved_documents.jsonl로 저장합니다.",
  vectorstore: "승인된 approved_documents.jsonl을 기준으로 원문/보고서 core vectorstore와 특허별 wiki vectorstore를 분리해서 다시 만듭니다.",
  query: "질문이 들어오면 가벼운 의도 판단 뒤 특허 원문/보고서를 core로 검색합니다. 최신/시장/경쟁사처럼 web 필요 질문일 때만 특허별 wiki gate를 먼저 확인하고, 없으면 웹 근거를 붙입니다.",
};

const workflowGraphInfo = {
  chat: {
    title: "챗봇 답변 워크플로우",
    endpoint: "/api/v1/patent-chat/chat/mermaid",
    summary: "질문 맥락을 정리한 뒤 가벼운 LLM/룰 기반 의도 라우터가 검색 위치와 답변 형식을 정합니다. 원문/보고서 질문은 core 근거만 쓰고, web 필요 질문만 특허별 wiki gate와 Tavily 경로로 넘어갑니다.",
    steps: [
      ["resolve_history_context", "이전 대화와 선택 특허를 현재 질문 맥락으로 정리"],
      ["route_question", "의도, 웹검색 필요 여부, 표/다이어그램 필요 여부 판단"],
      ["retrieve_wiki_context", "web 필요 질문일 때만 감사 후 승인된 특허별 wiki vectorstore 근거 검색"],
      ["retrieve_web_context", "wiki 근거가 없고 최신성/외부 정보가 필요할 때만 웹 근거 수집"],
      ["answer_from_patent_context", "특허 원문/보고서 core vectorstore와 wiki/web 보강 근거로 답변 생성"],
      ["finish_answer", "근거 카드, 성능 지표, 워크플로우 trace 반환"],
    ],
  },
  application: {
    title: "특허 출원 도우미 워크플로우",
    endpoint: "/api/v1/application/chat/mermaid",
    summary: "실패특허 원본 PDF가 있는 케이스를 먼저 선택한 뒤, 공용 공식팩 vectorstore와 선택 케이스 전용 vectorstore를 함께 검색합니다. 여러 실패특허가 있어도 답변에는 선택된 케이스 하나만 섞입니다.",
    steps: [
      ["resolve_application_history", "후속 질문이면 이전 질문/답변을 검색 질의에 반영"],
      ["validate_failed_patent_case", "failed_patent_id와 원본 PDF, 케이스 전용 vectorstore 상태 확인"],
      ["route_application_question", "출원 의도, 외부 보강 필요 여부, 표/다이어그램 답변 형식 판단"],
      ["retrieve_application_context", "공용 공식팩 vectorstore와 선택 실패특허 vectorstore를 분리 검색 후 병합"],
      ["retrieve_application_external_context", "선행기술/시장/최신 동향이 필요하면 외부 보강 검색"],
      ["answer_application_question", "출원 절차, 실패 요인, 피드백, 다음 액션을 근거 기반으로 생성"],
      ["finish_application_answer", "근거 카드, 품질 지표, agent trace 정리"],
    ],
  },
  wiki: {
    title: "Wiki 감사/승인 워크플로우",
    endpoint: "/api/v1/wiki/agent/mermaid",
    summary: "wiki와 특허/보고서 데이터를 감사하고, 나쁜 데이터 후보를 제외한 승인 Markdown/JSONL만 vectorstore에 반영합니다.",
    steps: [
      ["route_request", "audit/review/apply/refresh/status 모드 분기"],
      ["run_audit", "EMPTY, OCR_NOISE, SECRET, DUPLICATE 등 품질 규칙 검사"],
      ["load_review", "사람이 확인할 review.md와 finding 목록 로드"],
      ["apply_review", "제외 항목을 반영해 승인 context/document 저장"],
      ["refresh_vectorstore", "승인 데이터 기준으로 vectorstore 원자적 갱신"],
      ["collect_status", "현재 감사/승인/vectorstore 상태 반환"],
    ],
  },
  ingestion: {
    title: "전처리/RAG 재색인 워크플로우",
    endpoint: "/api/v1/patent-chat/ingestion/mermaid",
    summary: "특허별/전체 인덱스를 재생성하고 승인 vectorstore 갱신 시 원문/보고서 core와 특허별 wiki를 분리합니다.",
    steps: [
      ["inspect_request", "요청 scope와 특허 ID, Hybrid Retrieval 엔진 상태 확인"],
      ["run_reindex", "scope에 따라 특허별/global/business 인덱스 생성"],
      ["reviewed vectorstore refresh", "옵션이 켜지면 승인 데이터 기반 vectorstore 갱신"],
      ["finish_ingestion", "Swagger/UI에서 확인할 결과와 trace 반환"],
    ],
  },
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

async function apiForm(path, formData) {
  const response = await fetch(path, {
    method: "POST",
    body: formData,
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

function inlineMarkdown(value) {
  return escapeHtml(value)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

function stripMermaidFence(value) {
  return String(value || "")
    .replace(/^```mermaid\s*/i, "")
    .replace(/^```\s*/i, "")
    .replace(/```\s*$/i, "")
    .trim();
}

function cleanMermaidLabel(value) {
  return String(value || "")
    .replace(/<[^>]+>/g, " ")
    .replace(/^[\[\(\{]+|[\]\)\}]+$/g, "")
    .replace(/^"+|"+$/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function parseMermaid(code) {
  const nodes = new Map();
  const edges = [];
  const nodeId = "[A-Za-z_][A-Za-z0-9_]*|__[A-Za-z0-9_]+__";
  const nodePattern = new RegExp(`(${nodeId})\\s*(?:\\[([^\\]]+)\\]|\\(([^\\)]+)\\)|\\{([^\\}]+)\\})`, "g");
  const edgePattern = new RegExp(
    `(${nodeId})(?:\\[[^\\]]*\\]|\\([^\\)]*\\)|\\{[^\\}]*\\})?\\s*(?:(-->|---|==>)\\s*(?:\\|([^|]+)\\|)?|-\\.\\s*([^.]*)\\s*\\.->|-.->)\\s*(${nodeId})`,
    "g",
  );

  stripMermaidFence(code).split("\n").forEach((rawLine) => {
    const line = rawLine.trim().replace(/;$/, "");
    if (!line || line.startsWith("%%") || /^(flowchart|graph|sequenceDiagram|classDef|class\s)/i.test(line)) return;

    [...line.matchAll(nodePattern)].forEach((match) => {
      const id = match[1];
      const label = cleanMermaidLabel(match[2] || match[3] || match[4] || id);
      if (!nodes.has(id)) nodes.set(id, label || id);
    });

    [...line.matchAll(edgePattern)].forEach((match) => {
      const from = match[1];
      const label = cleanMermaidLabel(match[3] || match[4] || "");
      const to = match[5];
      if (!nodes.has(from)) nodes.set(from, from);
      if (!nodes.has(to)) nodes.set(to, to);
      edges.push({ from, to, label });
    });
  });

  return { nodes, edges };
}

function renderMermaidDiagram(code) {
  const parsed = parseMermaid(code);
  const nodeLabel = (id) => parsed.nodes.get(id) || id;
  if (!parsed.nodes.size && !parsed.edges.length) {
    return `<pre>${escapeHtml(stripMermaidFence(code))}</pre>`;
  }
  const edges = parsed.edges.length
    ? parsed.edges.map((edge, index) => `
        <div class="diagram-edge">
          <strong>${index + 1}</strong>
          <span class="diagram-from">${escapeHtml(nodeLabel(edge.from))}</span>
          <b>→</b>
          <span class="diagram-to">${escapeHtml(nodeLabel(edge.to))}</span>
          ${edge.label ? `<em>${escapeHtml(edge.label)}</em>` : ""}
        </div>`).join("")
    : [...parsed.nodes.entries()]
        .map(([id, label], index) => `<span class="diagram-node" title="${escapeHtml(id)}">${index + 1}. ${escapeHtml(label)}</span>`)
        .join("");
  return `
    <div class="mermaid-render">
      <div class="${parsed.edges.length ? "diagram-edge-list" : "diagram-node-row"}">${edges}</div>
    </div>
  `;
}

function splitTableRow(line) {
  let value = line.trim();
  if (value.startsWith("|")) value = value.slice(1);
  if (value.endsWith("|")) value = value.slice(0, -1);
  return value.split("|").map((cell) => cell.trim());
}

function isTableSeparator(line) {
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line || "");
}

function renderMarkdownTable(lines, startIndex) {
  const header = splitTableRow(lines[startIndex]);
  const rows = [];
  let index = startIndex + 2;
  while (index < lines.length && lines[index].includes("|") && lines[index].trim()) {
    rows.push(splitTableRow(lines[index]));
    index += 1;
  }
  const headHtml = header.map((cell) => `<th>${inlineMarkdown(cell)}</th>`).join("");
  const bodyHtml = rows
    .map((row) => `<tr>${header.map((_, cellIndex) => `<td>${inlineMarkdown(row[cellIndex] || "")}</td>`).join("")}</tr>`)
    .join("");
  return {
    html: `<div class="table-wrap"><table class="answer-table"><thead><tr>${headHtml}</tr></thead><tbody>${bodyHtml}</tbody></table></div>`,
    nextIndex: index,
  };
}

function renderAnswerHtml(text) {
  const lines = String(text || "").split("\n");
  const html = [];
  let inList = false;
  let listType = null;
  const closeList = () => {
    if (inList) {
      html.push(`</${listType}>`);
      inList = false;
      listType = null;
    }
  };

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    const trimmed = line.trim();
    if (!trimmed) {
      closeList();
      continue;
    }

    if (trimmed.startsWith("```")) {
      closeList();
      const lang = trimmed.replace(/^```/, "").trim().toLowerCase();
      const block = [];
      i += 1;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        block.push(lines[i]);
        i += 1;
      }
      const code = block.join("\n");
      html.push(lang === "mermaid" ? renderMermaidDiagram(code) : `<pre><code>${escapeHtml(code)}</code></pre>`);
      continue;
    }

    if (i + 1 < lines.length && line.includes("|") && isTableSeparator(lines[i + 1])) {
      closeList();
      const table = renderMarkdownTable(lines, i);
      html.push(table.html);
      i = table.nextIndex - 1;
      continue;
    }

    if (trimmed.startsWith("## ")) {
      closeList();
      html.push(`<h2>${inlineMarkdown(trimmed.slice(3))}</h2>`);
      continue;
    }

    if (trimmed.startsWith("### ")) {
      closeList();
      html.push(`<h3>${inlineMarkdown(trimmed.slice(4))}</h3>`);
      continue;
    }

    if (/^\d+\.\s+/.test(trimmed)) {
      if (!inList || listType !== "ol") {
        closeList();
        html.push("<ol>");
        inList = true;
        listType = "ol";
      }
      html.push(`<li>${inlineMarkdown(trimmed.replace(/^\d+\.\s+/, ""))}</li>`);
      continue;
    }

    if (/^[-*]\s+/.test(trimmed)) {
      if (!inList || listType !== "ul") {
        closeList();
        html.push("<ul>");
        inList = true;
        listType = "ul";
      }
      html.push(`<li>${inlineMarkdown(trimmed.replace(/^[-*]\s+/, ""))}</li>`);
      continue;
    }

    closeList();
    html.push(`<p>${inlineMarkdown(line)}</p>`);
  }
  closeList();
  return html.join("");
}

function appendMessage(text, className, rich = false, containerId = "messages") {
  const message = document.createElement("div");
  message.className = `message ${className}`;
  if (rich) {
    message.innerHTML = renderAnswerHtml(text);
  } else {
    message.textContent = text;
  }
  $(containerId).appendChild(message);
  $(containerId).scrollTop = $(containerId).scrollHeight;
  return message;
}

function rememberHistory(kind, question, answer, extra = {}) {
  const key = kind === "application" ? "applicationHistory" : "chatHistory";
  state[key].push({ question, answer: String(answer || "").slice(0, 3000), ...extra });
  state[key] = state[key].slice(-6);
}

function focusAnswerStart(message) {
  window.requestAnimationFrame(() => {
    message.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function renderAnswerProgressively(message, answer) {
  const text = String(answer || "");
  if (!text) {
    message.textContent = "";
    return;
  }
  const step = text.length > 2500 ? 180 : 90;
  message.textContent = "";
  for (let index = step; index < text.length; index += step) {
    message.textContent = text.slice(0, index);
    focusAnswerStart(message);
    await delay(10);
  }
  message.innerHTML = renderAnswerHtml(text);
  focusAnswerStart(message);
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

function sourceTitle(source) {
  return (
    source?.display_title ||
    source?.metadata?.source_title ||
    source?.title ||
    source?.metadata?.title ||
    source?.metadata?.section_title ||
    source?.metadata?.file_name ||
    source?.source_type ||
    source?.label ||
    "근거 자료"
  );
}

function sourceLocation(source) {
  const chunk = source?.metadata?.chunk_index ?? source?.metadata?.chunk_id;
  return (
    source?.location_label ||
    source?.metadata?.location_label ||
    [
      source?.source_type,
      source?.page_no ? `p.${source.page_no}` : "",
      source?.metadata?.section_title ? `섹션: ${source.metadata.section_title}` : "",
      chunk ? `청크: ${chunk}` : "",
    ].filter(Boolean).join(" · ") ||
    "근거 위치 정보 없음"
  );
}

function sourcePath(source) {
  return (
    source?.source_path ||
    source?.metadata?.source_path_for_display ||
    source?.metadata?.relative_source_path ||
    source?.metadata?.source_path ||
    source?.metadata?.file_name ||
    source?.url ||
    ""
  );
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlightedEvidence(source) {
  let text = escapeHtml(source?.snippet || source?.metadata?.evidence_excerpt || "");
  const terms = [...new Set([...(source?.match_terms || []), ...(source?.metadata?.match_terms || [])].filter(Boolean))].slice(0, 12);
  terms.forEach((term) => {
    const pattern = new RegExp(`(${escapeRegExp(term)})`, "gi");
    text = text.replace(pattern, "<mark>$1</mark>");
  });
  return text;
}

function sourceModalBody(source) {
  return `${detailList([
    ["문서 제목", sourceTitle(source)],
    ["근거 위치", sourceLocation(source)],
    ["기존 인용", source?.metadata?.citation_label || source?.label],
    ["자료 유형", source?.source_type],
    ["페이지", source?.page_no],
    ["파일/경로", sourcePath(source)],
    ["URL", source?.url],
  ])}<h2>근거로 사용된 부분</h2><pre class="source-highlight">${highlightedEvidence(source)}</pre><h2>Metadata</h2>${jsonBlock(source?.metadata)}`;
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
  select.value = "__all__";
}

function renderApplicationCases(selectedId = null) {
  const select = $("applicationCaseSelect");
  if (!select) return;
  const current = selectedId || select.value;
  select.innerHTML = `<option value="">케이스를 업로드하거나 선택하세요</option>`;
  state.applicationCases.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.case_id;
    const count = item.document_count ?? 0;
    option.textContent = `${item.case_id} · ${item.title || item.case_id} · 문서 ${count}개`;
    select.appendChild(option);
  });
  if (current && state.applicationCases.some((item) => item.case_id === current)) {
    select.value = current;
  }
}

async function loadApplicationCases(selectedId = null) {
  const data = await api("/api/v1/application/failed-patents");
  state.applicationCases = data.items || [];
  renderApplicationCases(selectedId);
  return data;
}

function showTab(tabId) {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabId);
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === tabId);
  });
  if (tabId === "workflowTab" && !$("workflowDiagram").dataset.loaded) {
    loadChatWorkflow().catch((error) => setStatus(error.message));
  }
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
        <button type="button" data-action="files">파일</button>
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
    article.querySelector('[data-action="files"]').addEventListener("click", async () => {
      const files = await api(`/api/v1/chatbot/patents/${encodeURIComponent(patent.patent_id)}/files?limit=80`);
      showModal(`${patent.patent_id} files`, jsonBlock(files));
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

function appendAnswerMeta(metrics, sourceCards, containerId = "messages") {
  const meta = document.createElement("div");
  meta.className = "answer-meta";
  const quality = metrics?.answer_quality || {};
  meta.innerHTML = [
    `engine ${metrics?.engine || metrics?.mode || "-"}`,
    `scope ${metrics?.scope || "-"}`,
    `mode ${metrics?.answer_mode || metrics?.mode || "-"}`,
    `근거 ${(sourceCards || []).length}개`,
    `confidence ${metrics?.confidence_score ?? metrics?.hit_count ?? "-"}`,
    quality.composite_score !== undefined ? `quality ${quality.composite_score} (${quality.grade || "-"})` : "",
  ].filter(Boolean).map((item) => `<span>${escapeHtml(item)}</span>`).join("");
  $(containerId).appendChild(meta);
}

function appendSources(sourceCards, containerId = "messages") {
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
    const title = sourceTitle(source);
    const location = sourceLocation(source);
    const originalLabel = source?.metadata?.citation_label || source.label || "";
    card.innerHTML = `
      <button class="source-card-main" type="button" aria-label="${escapeHtml(title)} 근거 보기">
        <strong>${escapeHtml(title)}</strong>
        ${originalLabel ? `<span>${escapeHtml(originalLabel)}</span>` : ""}
      </button>
      <div class="chip-row">
        ${chip(source.source_type)}
        ${chip(location, "location")}
      </div>
      <p>${escapeHtml(source.snippet || "")}</p>
      <div class="source-actions">
        <button type="button">근거 보기</button>
        ${source.url ? `<a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">파일</a>` : ""}
      </div>
    `;
    const openSource = () => showModal(title, sourceModalBody(source));
    card.querySelector(".source-card-main").addEventListener("click", openSource);
    card.querySelector(".source-actions button").addEventListener("click", openSource);
    list.appendChild(card);
  });
  details.appendChild(list);
  $(containerId).appendChild(details);
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
  loadApplicationCases().catch(() => {
    state.applicationCases = [];
    renderApplicationCases();
  });
  const vector = status.vectorstore_status || config.vectorstore || {};
  const engine = config.rag_engine?.available ? "Hybrid Retrieval" : "fallback";
  setStatus(`특허 ${config.patent_count ?? state.patents.length}개 · 문서 ${vector.global?.document_count ?? "-"}개 · ${engine}`);
  api("/api/v1/patent-chat/patent-summary-cards")
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
  return loadWorkflowGraph("wiki");
}

async function loadChatWorkflow() {
  return loadWorkflowGraph("chat");
}

async function loadApplicationWorkflow() {
  return loadWorkflowGraph("application");
}

async function loadIngestionWorkflow() {
  return loadWorkflowGraph("ingestion");
}

function workflowInfoHtml(type) {
  const info = workflowGraphInfo[type] || workflowGraphInfo.wiki;
  const steps = info.steps
    .map(([name, description]) => `
      <button class="workflow-step" type="button" data-step-name="${escapeHtml(name)}" data-step-description="${escapeHtml(description)}">
        <strong>${escapeHtml(name)}</strong>
        <span>${escapeHtml(description)}</span>
      </button>
    `)
    .join("");
  return `
    <h3>${escapeHtml(info.title)}</h3>
    <p>${escapeHtml(info.summary)}</p>
    <div class="workflow-step-grid">${steps}</div>
  `;
}

function bindWorkflowStepDetails() {
  document.querySelectorAll(".workflow-step").forEach((button) => {
    button.addEventListener("click", () => {
      showModal(
        button.dataset.stepName || "워크플로우 단계",
        `<p>${escapeHtml(button.dataset.stepDescription || "")}</p>`,
      );
    });
  });
}

async function loadWorkflowGraph(type) {
  const info = workflowGraphInfo[type] || workflowGraphInfo.wiki;
  const graph = await api(info.endpoint);
  state.mermaid = graph.diagram || "";
  $("workflowDetail").innerHTML = workflowInfoHtml(type);
  $("workflowDiagram").innerHTML = state.mermaid ? renderMermaidDiagram(state.mermaid) : `<div class="empty">그래프가 없습니다.</div>`;
  $("workflowDiagram").dataset.loaded = type;
  $("workflowMermaid").textContent = state.mermaid || "그래프가 없습니다.";
  bindWorkflowStepDetails();
  setStatus(`${info.title} 로드 완료`);
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
    const result = await api("/api/v1/patent-chat/reindex", {
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
    const result = await api("/api/v1/patent-chat/global/reindex", {
      method: "POST",
      body: JSON.stringify({ force_rebuild: false, refresh_reviewed_vectorstore: false }),
    });
    setStatus(`전체 인덱스 확인 완료 · ${result.engine || "-"}`);
    showModal("전체 인덱스 결과", jsonBlock(result));
  } finally {
    setBusy(button, false);
  }
}

async function prepareApplicationData() {
  const button = $("prepareApplicationButton");
  setBusy(button, true, "준비 중");
  try {
    const preprocess = await api("/api/v1/application/preprocess", {
      method: "POST",
      body: JSON.stringify({ refresh_index: true }),
    });
    const refresh = await api("/api/v1/application/index/refresh", { method: "POST" });
    const cases = await loadApplicationCases();
    setStatus(`출원 데이터 준비 완료 · 파일 ${preprocess.active_file_count ?? 0}개 · index ${refresh.document_count ?? 0}개`);
    showModal(
      "출원 데이터 준비",
      jsonBlock({ preprocess, refresh, failed_patent_cases: cases }),
    );
  } finally {
    setBusy(button, false);
  }
}

async function showApplicationStatus() {
  const status = await api("/api/v1/application/status");
  await loadApplicationCases();
  setStatus(`출원 도우미 · index ${status.index_exists ? "있음" : "없음"} · 문서 ${status.document_count ?? 0}개 · 다운로드 실패 ${status.download_report?.failure_count ?? 0}건`);
  showModal("출원 도우미 상태", jsonBlock(status));
}

async function refreshApprovedVectorstore() {
  const button = $("refreshApprovedVectorstoreButton");
  setBusy(button, true, "갱신 중");
  try {
    const result = await api("/api/v1/chatbot/preprocess/run", {
      method: "POST",
      body: JSON.stringify({ mode: "refresh_vectorstore", use_reviewed: true, refresh_application: false }),
    });
    const source = result.vectorstore?.source || "approved";
    setStatus(`승인 Vectorstore 갱신 완료 · ${source}`);
    showModal("승인 Vectorstore 갱신", jsonBlock(result));
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
    const path = selected === "__all__" ? "/api/v1/patent-chat/global/chat" : "/api/v1/patent-chat/chat";
    const data = await api(path, {
      method: "POST",
      body: JSON.stringify({
        question: text,
        patent_id: selected === "__all__" ? null : selected,
        user_id: "browser-ui",
        chat_history: state.chatHistory,
        context_patent_id: selected === "__all__" ? null : selected,
      }),
    });
    await renderAnswerProgressively(pending, data.answer || "");
    appendAnswerMeta(data.metrics || {}, data.source_cards || []);
    appendSources(data.source_cards || []);
    focusAnswerStart(pending);
    rememberHistory("chat", text, data.answer, { patent_id: selected === "__all__" ? null : selected });
    setStatus(`답변 완료 · 근거 ${(data.source_cards || []).length}개`);
  } catch (error) {
    pending.textContent = `요청 실패: ${error.message}`;
  } finally {
    setBusy(button, false);
    $("question").focus();
  }
}

async function uploadFailedPatentCase() {
  const pdfInput = $("failedPatentPdfInput");
  const rejectionInput = $("failedPatentRejectionInput");
  const pdf = pdfInput.files?.[0];
  if (!pdf) {
    setStatus("실패특허 원본 PDF를 먼저 선택하세요.");
    return;
  }
  const button = $("uploadFailedPatentButton");
  setBusy(button, true, "업로드 중");
  try {
    const formData = new FormData();
    formData.append("original_pdf", pdf);
    const rejection = rejectionInput.files?.[0];
    if (rejection) formData.append("rejection_file", rejection);
    const title = $("failedPatentTitleInput").value.trim();
    if (title) formData.append("title", title);
    formData.append("reviewer", "browser-ui");
    formData.append("refresh_index", "true");
    const result = await apiForm("/api/v1/application/failed-patents/upload", formData);
    await loadApplicationCases(result.case_id);
    pdfInput.value = "";
    rejectionInput.value = "";
    setStatus(`실패특허 케이스 생성 완료 · ${result.case_id} · 문서 ${result.index?.document_count ?? 0}개`);
    showModal("실패특허 케이스", jsonBlock(result));
  } finally {
    setBusy(button, false);
  }
}

async function askApplication() {
  const text = $("applicationQuestion").value.trim();
  if (!text) return;
  const caseId = $("applicationCaseSelect").value;
  if (!caseId) {
    appendMessage("먼저 실패특허 원본 PDF를 업로드하거나 기존 케이스를 선택하세요.", "assistant", false, "applicationMessages");
    setStatus("출원 도우미는 실패특허 케이스 선택 후 질문할 수 있습니다.");
    return;
  }
  appendMessage(text, "user", false, "applicationMessages");
  $("applicationQuestion").value = "";
  const button = $("sendApplicationButton");
  setBusy(button, true, "생성 중");
  const pending = appendMessage("공식팩에서 근거를 찾고 출원 도우미 답변을 구성합니다.", "assistant", false, "applicationMessages");
  try {
    const data = await api("/api/v1/application/chat", {
      method: "POST",
      body: JSON.stringify({
        question: text,
        user_id: "browser-ui",
        failed_patent_id: caseId,
        chat_history: state.applicationHistory,
        top_k: 6,
        refresh_index: false,
      }),
    });
    await renderAnswerProgressively(pending, data.answer || "");
    appendAnswerMeta(data.metrics || {}, data.source_cards || [], "applicationMessages");
    appendSources(data.source_cards || [], "applicationMessages");
    focusAnswerStart(pending);
    rememberHistory("application", text, data.answer, { patent_id: "patent_application", failed_patent_id: caseId });
    setStatus(`출원 답변 완료 · 근거 ${(data.source_cards || []).length}개`);
  } catch (error) {
    pending.textContent = `요청 실패: ${error.message}`;
  } finally {
    setBusy(button, false);
    $("applicationQuestion").focus();
  }
}

function bindEvents() {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => showTab(button.dataset.tab));
  });
  $("reloadButton").addEventListener("click", () => loadBaseData().catch((error) => setStatus(error.message)));
  $("loadDataButton").addEventListener("click", () => loadBaseData().catch((error) => setStatus(error.message)));
  $("refreshApprovedVectorstoreButton").addEventListener("click", () => refreshApprovedVectorstore().catch((error) => setStatus(error.message)));
  $("reindexButton").addEventListener("click", () => reindexSelected().catch((error) => setStatus(error.message)));
  $("globalReindexButton").addEventListener("click", () => checkGlobalIndex().catch((error) => setStatus(error.message)));
  $("runAuditButton").addEventListener("click", () => runAudit().catch((error) => setStatus(error.message)));
  $("loadReviewButton").addEventListener("click", () => loadReview().catch((error) => setStatus(error.message)));
  $("applyAuditButton").addEventListener("click", () => applyAudit().catch((error) => setStatus(error.message)));
  $("loadChatWorkflowButton").addEventListener("click", () => loadChatWorkflow().catch((error) => setStatus(error.message)));
  $("loadApplicationWorkflowButton").addEventListener("click", () => loadApplicationWorkflow().catch((error) => setStatus(error.message)));
  $("loadWorkflowButton").addEventListener("click", () => loadWorkflow().catch((error) => setStatus(error.message)));
  $("loadIngestionWorkflowButton").addEventListener("click", () => loadIngestionWorkflow().catch((error) => setStatus(error.message)));
  $("prepareApplicationButton").addEventListener("click", () => prepareApplicationData().catch((error) => setStatus(error.message)));
  $("applicationStatusButton").addEventListener("click", () => showApplicationStatus().catch((error) => setStatus(error.message)));
  $("uploadFailedPatentButton").addEventListener("click", () => uploadFailedPatentCase().catch((error) => setStatus(error.message)));
  $("applicationCaseSelect").addEventListener("change", () => {
    state.applicationHistory = [];
    setStatus($("applicationCaseSelect").value ? `출원 케이스 선택 · ${$("applicationCaseSelect").value}` : "출원 케이스를 선택하세요");
  });
  $("sendButton").addEventListener("click", ask);
  $("sendApplicationButton").addEventListener("click", askApplication);
  $("question").addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
    event.preventDefault();
    ask();
  });
  $("applicationQuestion").addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
    event.preventDefault();
    askApplication();
  });
  document.querySelectorAll("[data-flow]").forEach((button) => {
    button.addEventListener("click", () => {
      $("workflowDetail").innerHTML = `<h3>${escapeHtml(button.textContent || "워크플로우 단계")}</h3><p>${escapeHtml(workflowText[button.dataset.flow] || "")}</p>`;
    });
  });
  $("closeModalButton").addEventListener("click", () => $("detailModal").classList.remove("open"));
  $("detailModal").addEventListener("click", (event) => {
    if (event.target.id === "detailModal") $("detailModal").classList.remove("open");
  });
}

bindEvents();
loadBaseData().catch((error) => setStatus(error.message));
