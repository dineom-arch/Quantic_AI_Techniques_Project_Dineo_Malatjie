"use strict";

const state = { sessionId: null, identity: null, busy: false, tourReturnFocus: null };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const STATUS_LABELS = {
  answered: "Grounded answer",
  insufficient_evidence: "More evidence needed",
  clarification_required: "Clarification required",
  action_confirmation_required: "Your confirmation is required",
  forbidden: "Private information protected",
  not_found: "Record not found",
  out_of_scope: "Outside Compass scope",
  tool_error: "Service issue",
};

const TOOL_LABELS = {
  search_knowledge_documents: "Search policy knowledge",
  lookup_employee_profile: "Check employee profile",
  check_pto_balance: "Check PTO balance",
  lookup_active_assignment: "Check active assignment",
  lookup_travel_authorization: "Check travel authorisation",
  get_mock_travel_booking: "Retrieve travel booking",
  get_per_diem_rate: "Retrieve per diem rate",
  get_mock_expense_claim: "Retrieve expense claim",
  resolve_approval_role: "Resolve approval role",
  create_mock_travel_request: "Create mock travel request",
  create_mock_hr_ticket: "Create mock HR ticket",
};

function initials(name) {
  return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

function make(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function requestJson(url, options = {}, timeoutMs = 15000) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal, headers: { "Content-Type": "application/json", ...(options.headers || {}) } });
    if (!response.ok) throw new Error("request_failed");
    return await response.json();
  } finally {
    window.clearTimeout(timeout);
  }
}

async function signIn() {
  const button = $("#login-button"); button.disabled = true; button.textContent = "Signing in…";
  $("#login-error").hidden = true;
  try {
    const session = await requestJson("/auth/demo-session", { method: "POST" });
    state.sessionId = session.session_id;
    state.identity = { displayName: session.display_name, givenName: session.given_name, jobTitle: session.job_title };
    sessionStorage.setItem("meridianSession", JSON.stringify({ sessionId: state.sessionId, identity: state.identity }));
    openApplication();
  } catch (_) {
    $("#login-error").textContent = "The demonstration session could not be started. Please try again.";
    $("#login-error").hidden = false; button.disabled = false;
  } finally { button.textContent = "Continue with Enterprise Identity"; }
}

function openApplication() {
  $("#login-view").hidden = true; $("#app-shell").hidden = false;
  const { displayName, jobTitle } = state.identity;
  const givenName = state.identity.givenName || displayName.split(" ")[0];
  $("#sidebar-name").textContent = displayName; $("#sidebar-role").textContent = jobTitle;
  $("#header-identity").textContent = `${displayName.split(" ")[0]} • ${jobTitle}`;
  $("#welcome-heading").textContent = `Hi ${givenName}, what can I help you with?`;
  $("#identity-initials").textContent = initials(displayName);
  $("#context-initials").textContent = initials(displayName);
  $("#context-name").textContent = displayName; $("#context-role").textContent = jobTitle;
  checkHealth(); $("#message-input").focus();
}

async function checkHealth() {
  const indicator = $("#health-indicator");
  try {
    const health = await requestJson("/health");
    const ready = health.status === "healthy";
    indicator.classList.toggle("degraded", !ready);
    indicator.lastElementChild.textContent = ready ? "Compass ready" : "Compass service degraded";
  } catch (_) {
    indicator.classList.add("degraded"); indicator.lastElementChild.textContent = "Compass status unavailable";
  }
}

function showView(name) {
  $$(".view").forEach((view) => { view.hidden = view.id !== `view-${name}`; view.classList.toggle("active-view", !view.hidden); });
  $$(".nav-item").forEach((item) => { const active = item.dataset.view === name; item.classList.toggle("active", active); active ? item.setAttribute("aria-current", "page") : item.removeAttribute("aria-current"); });
  $("#main-content").focus();
}

function addUserMessage(message) {
  $("#welcome-state").hidden = true;
  $("#messages").append(make("div", "message-user", message));
}

function sourcePanel(payload) {
  if (!payload.citations.length && !payload.tool_trace.length) return null;
  const details = make("details", "evidence-disclosure");
  details.append(make("summary", "", "View sources and system trace"));
  const grid = make("div", "evidence-grid");
  const sources = make("section"); sources.setAttribute("aria-label", "Verified sources"); sources.append(make("h3", "", "Sources"));
  if (!payload.citations.length) sources.append(make("p", "", "No document citations were returned for this response."));
  payload.citations.forEach((citation) => {
    const card = make("article", "source-card");
    card.append(make("strong", "", citation.title), make("span", "", `${citation.document_id} · ${citation.section}`), make("small", "", citation.snippet));
    sources.append(card);
  });
  const trace = make("section"); trace.setAttribute("aria-label", "Sanitised system trace"); trace.append(make("h3", "", "System trace"));
  const timeline = make("ol", "trace-list");
  payload.tool_trace.forEach((entry) => {
    const label = entry.tool_name ? (TOOL_LABELS[entry.tool_name] || entry.tool_name.replaceAll("_", " ")) : entry.event.replaceAll("_", " ");
    const item = make("li", "", label); item.append(make("span", "", entry.status === "ok" ? "Completed" : entry.status.replaceAll("_", " "))); timeline.append(item);
  });
  trace.append(timeline); grid.append(sources, trace); details.append(grid); return details;
}

function confirmationPanel() {
  const panel = make("section", "confirmation-panel"); panel.setAttribute("aria-label", "Mock action confirmation");
  panel.append(make("h3", "", "Ready to create a mock travel request"), make("p", "", "This is a demonstration action. It will not book travel or submit a real enterprise request."));
  const actions = make("div", "confirmation-actions");
  const confirm = make("button", "button button-primary", "Create mock request"); confirm.type = "button";
  const cancel = make("button", "button button-secondary", "Not now"); cancel.type = "button";
  confirm.addEventListener("click", () => sendMessage("Yes, create the mock personal travel extension request using the details we just reviewed.", true));
  cancel.addEventListener("click", () => { panel.replaceChildren(make("p", "", "No mock request was created.")); });
  actions.append(confirm, cancel); panel.append(actions); return panel;
}

function addAssistantMessage(payload) {
  const attentionStatuses = new Set(["action_confirmation_required", "insufficient_evidence", "forbidden", "tool_error"]);
  const article = make("article", `message-assistant${attentionStatuses.has(payload.status) ? " attention" : ""}`);
  const header = make("div", "response-label"); header.append(make("strong", "", "Compass"), make("span", "status-badge", STATUS_LABELS[payload.status] || payload.status));
  article.append(header, make("p", "answer-copy", payload.answer));
  if (payload.status === "action_confirmation_required") article.append(confirmationPanel());
  const evidence = sourcePanel(payload); if (evidence) article.append(evidence);
  $("#messages").append(article); article.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function sendMessage(message, confirmAction = false) {
  if (state.busy || !message.trim()) return;
  state.busy = true; addUserMessage(message.trim());
  $("#loading-state").hidden = false; $("#send-button").disabled = true; $("#message-input").disabled = true;
  try {
    const payload = await requestJson("/chat", { method: "POST", body: JSON.stringify({ message: message.trim(), session_id: state.sessionId, confirm_action: confirmAction }) });
    addAssistantMessage(payload);
  } catch (_) {
    addAssistantMessage({ answer: "Compass could not complete the request. Please check the service status and try again.", status: "tool_error", citations: [], tool_trace: [] });
  } finally {
    state.busy = false; $("#loading-state").hidden = true; $("#send-button").disabled = false; $("#message-input").disabled = false; $("#message-input").value = ""; $("#message-input").focus();
  }
}

function restoreSession() {
  try { const saved = JSON.parse(sessionStorage.getItem("meridianSession")); if (saved?.sessionId && saved?.identity) { state.sessionId = saved.sessionId; state.identity = saved.identity; openApplication(); return true; } } catch (_) { sessionStorage.removeItem("meridianSession"); }
  return false;
}

async function openTour() {
  state.tourReturnFocus = document.activeElement;
  const modal = $("#tour-modal"); modal.hidden = false; document.body.style.overflow = "hidden";
  try {
    const response = await fetch("/static/media/meridian-compass-60-second-tour.mp4", { method: "HEAD" });
    if (response.ok) { $("#tour-video").hidden = false; $("#tour-fallback").hidden = true; }
  } catch (_) { /* polished fallback remains visible */ }
  $("#close-tour").focus();
}

function closeTour() {
  const video = $("#tour-video"); video.pause();
  $("#tour-modal").hidden = true; document.body.style.overflow = "";
  state.tourReturnFocus?.focus();
}

$("#login-button").addEventListener("click", signIn);
$("#open-tour").addEventListener("click", openTour);
$("#close-tour").addEventListener("click", closeTour);
$("#close-tour-secondary").addEventListener("click", closeTour);
$("#tour-modal").addEventListener("click", (event) => { if (event.target === $("#tour-modal")) closeTour(); });
document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !$("#tour-modal").hidden) closeTour(); });
$$(".nav-item").forEach((item) => item.addEventListener("click", () => showView(item.dataset.view)));
$$(".prompt-card").forEach((card) => card.addEventListener("click", () => { $("#message-input").value = card.textContent.trim(); $("#message-input").focus(); }));
$("#chat-form").addEventListener("submit", (event) => { event.preventDefault(); sendMessage($("#message-input").value); });
$("#message-input").addEventListener("keydown", (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); $("#chat-form").requestSubmit(); } });

if (!restoreSession()) $("#login-button").focus();
