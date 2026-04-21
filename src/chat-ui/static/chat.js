/**
 * CIMIC Project Advisor — Chat UI Client
 *
 * Connects to the FastAPI backend which proxies requests to Foundry Agent Service.
 * Uses Server-Sent Events (SSE) for real-time streaming of agent responses.
 */

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let currentConversationId = null;
let lastResponseId = null;    // Foundry response ID (for consent resume)
let lastUserMessage = "";     // last user message (for consent resume)
let isStreaming = false;
let pendingConsent = null;    // OAuth consent in progress
let streamHasError = false;   // error received during current stream
const conversations = []; // { id, title, messages[] }

// ---------------------------------------------------------------------------
// DOM refs
// ---------------------------------------------------------------------------
const messagesEl     = document.getElementById("messages");
const chatForm       = document.getElementById("chat-form");
const userInput      = document.getElementById("user-input");
const sendBtn        = document.getElementById("send-btn");
const newChatBtn     = document.getElementById("new-chat-btn");
const chatHistoryEl  = document.getElementById("chat-history");
const statusBadge    = document.getElementById("status-badge");

// ---------------------------------------------------------------------------
// Initialise
// ---------------------------------------------------------------------------
checkHealth();

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage();
});

userInput.addEventListener("input", () => {
  autoResize(userInput);
  sendBtn.disabled = userInput.value.trim() === "" || isStreaming;
});

userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

newChatBtn.addEventListener("click", startNewChat);

document.addEventListener("click", (e) => {
  if (e.target.classList.contains("suggestion")) {
    userInput.value = e.target.dataset.prompt;
    sendBtn.disabled = false;
    sendMessage();
  }
});

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------
async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (data.project_endpoint_configured) {
      setStatus("Ready", "connected");
    } else {
      setStatus("Not configured", "error");
    }
  } catch {
    setStatus("Offline", "error");
  }
}

function setStatus(text, state) {
  statusBadge.textContent = text;
  statusBadge.className = "status-badge " + (state || "");
}

// ---------------------------------------------------------------------------
// Chat management
// ---------------------------------------------------------------------------
function startNewChat() {
  currentConversationId = null;
  renderMessages([]);
  renderChatHistory();
}

// ---------------------------------------------------------------------------
// Send message & stream response via SSE
// ---------------------------------------------------------------------------
async function sendMessage() {
  const text = userInput.value.trim();
  if (!text || isStreaming) return;

  // Hide welcome message
  const welcome = messagesEl.querySelector(".welcome-message");
  if (welcome) welcome.remove();

  // Show user message
  appendMessage("user", text);
  lastUserMessage = text;
  userInput.value = "";
  autoResize(userInput);
  sendBtn.disabled = true;
  isStreaming = true;

  // Create agent message placeholder with typing indicator
  const agentMsgEl = appendMessage("agent", null, true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        conversation_id: currentConversationId,
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }

    // Read SSE stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let fullText = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Parse SSE events from the buffer
      const lines = buffer.split("\n");
      buffer = lines.pop(); // keep incomplete line in buffer

      let currentEvent = null;
      for (const line of lines) {
        if (line.startsWith("event:")) {
          currentEvent = line.slice(6).trim();
        } else if (line.startsWith("data:") && currentEvent) {
          const rawData = line.slice(5).trim();
          handleSSEEvent(currentEvent, rawData, agentMsgEl, (t) => {
            fullText += t;
          });
          currentEvent = null;
        } else if (line === "") {
          currentEvent = null;
        }
      }
    }

    // Finalize the message (skip if auth prompt or error is already showing)
    if (pendingConsent) return;
    if (streamHasError) { streamHasError = false; return; }

    removeTypingIndicator(agentMsgEl);
    renderMarkdown(agentMsgEl.querySelector(".message-content"), fullText);

    // Track conversation
    trackConversation(text, fullText);

  } catch (err) {
    removeTypingIndicator(agentMsgEl);
    agentMsgEl.querySelector(".message-content").textContent =
      `⚠️ Error: ${err.message}`;
  } finally {
    if (!pendingConsent) {
      isStreaming = false;
      sendBtn.disabled = userInput.value.trim() === "";
    }
  }
}

// ---------------------------------------------------------------------------
// SSE event handler
// ---------------------------------------------------------------------------
function handleSSEEvent(event, rawData, agentMsgEl, onDelta) {
  let data;
  try {
    data = JSON.parse(rawData);
  } catch {
    return;
  }

  switch (event) {
    case "conversation_id":
      currentConversationId = data.conversation_id;
      break;

    case "delta":
      removeTypingIndicator(agentMsgEl);
      onDelta(data.text);
      // Append raw text while streaming for live feel
      const content = agentMsgEl.querySelector(".message-content");
      content.textContent += data.text;
      scrollToBottom();
      break;

    case "done":
      break;

    case "error":
      removeTypingIndicator(agentMsgEl);
      streamHasError = true;
      agentMsgEl.querySelector(".message-content").textContent =
        `⚠️ ${data.error}`;
      break;

    case "response_id":
      lastResponseId = data.response_id;
      break;

    case "auth_required":
      // OAuth consent request — open consent_link in popup, then resume
      removeTypingIndicator(agentMsgEl);
      if (data.response_id) lastResponseId = data.response_id;
      pendingConsent = {
        consent_link: data.consent_link,
        server_label: data.server_label || "Databricks",
      };
      showConsentPrompt(agentMsgEl);
      break;

    case "auth_error":
      removeTypingIndicator(agentMsgEl);
      streamHasError = true;
      agentMsgEl.querySelector(".message-content").innerHTML =
        `<div class="auth-prompt">` +
          `<div class="auth-prompt-icon">⚠️</div>` +
          `<div class="auth-prompt-text">` +
            `<strong>Authentication Error</strong>` +
            `<p>Token expired or authorisation failed. Please refresh the page and try again.</p>` +
          `</div>` +
        `</div>`;
      break;
  }
}

// ---------------------------------------------------------------------------
// OAuth Consent Flow
// Ref: https://learn.microsoft.com/azure/foundry/agents/how-to/mcp-authentication
// ---------------------------------------------------------------------------
function showConsentPrompt(msgEl) {
  const content = msgEl.querySelector(".message-content");
  const label = escapeHtml(pendingConsent.server_label);
  content.innerHTML =
    `<div class="auth-prompt">` +
      `<div class="auth-prompt-icon">🔐</div>` +
      `<div class="auth-prompt-text">` +
        `<strong>Authorisation Required</strong>` +
        `<p><b>${label}</b> needs your permission to access data on your behalf. ` +
        `A sign-in window will open — please complete the consent and then click <b>Continue</b>.</p>` +
      `</div>` +
      `<div class="auth-prompt-actions">` +
        `<button class="auth-btn auth-btn-primary" id="auth-grant-btn">Sign In &amp; Authorise</button>` +
        `<button class="auth-btn auth-btn-secondary" id="auth-continue-btn" disabled>Continue</button>` +
      `</div>` +
    `</div>`;

  const grantBtn = content.querySelector("#auth-grant-btn");
  const continueBtn = content.querySelector("#auth-continue-btn");

  grantBtn.addEventListener("click", () => {
    // Open the consent_link from Foundry in a popup
    const popup = window.open(
      pendingConsent.consent_link,
      "oauth_consent",
      "width=600,height=700,popup=yes"
    );
    grantBtn.textContent = "✓ Opened — complete in popup";
    grantBtn.disabled = true;
    continueBtn.disabled = false;

    // Auto-detect when popup closes and highlight Continue
    if (popup) {
      const check = setInterval(() => {
        if (popup.closed) {
          clearInterval(check);
          continueBtn.classList.add("auth-btn-pulse");
          // Auto-continue after a short delay
          setTimeout(() => {
            if (pendingConsent) submitConsentResume(msgEl);
          }, 800);
        }
      }, 500);
    }
  });

  continueBtn.addEventListener("click", () => submitConsentResume(msgEl));
}

/**
 * After the user completes OAuth consent, resume the agent by submitting
 * a new response with previous_response_id (per Microsoft docs).
 */
async function submitConsentResume(agentMsgEl) {
  pendingConsent = null;

  // Show typing indicator while waiting for continued response
  const content = agentMsgEl.querySelector(".message-content");
  content.innerHTML =
    `<div class="typing-indicator"><span></span><span></span><span></span></div>`;

  try {
    const response = await fetch("/api/chat/consent-resume", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        conversation_id: currentConversationId,
        previous_response_id: lastResponseId,
        user_message: lastUserMessage,
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }

    // Read the continued SSE stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let fullText = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      let currentEvent = null;
      for (const line of lines) {
        if (line.startsWith("event:")) {
          currentEvent = line.slice(6).trim();
        } else if (line.startsWith("data:") && currentEvent) {
          handleSSEEvent(currentEvent, line.slice(5).trim(), agentMsgEl, (t) => { fullText += t; });
          currentEvent = null;
        } else if (line === "") {
          currentEvent = null;
        }
      }
    }

    // Another consent prompt may have appeared — don't overwrite it
    if (pendingConsent) return;
    if (streamHasError) { streamHasError = false; return; }

    removeTypingIndicator(agentMsgEl);
    renderMarkdown(agentMsgEl.querySelector(".message-content"), fullText);
    if (fullText) trackConversation("(continued after authorisation)", fullText);

  } catch (err) {
    content.textContent = `⚠️ Authorisation failed: ${err.message}`;
  } finally {
    if (!pendingConsent) {
      isStreaming = false;
      sendBtn.disabled = userInput.value.trim() === "";
    }
  }
}

// ---------------------------------------------------------------------------
// DOM helpers
// ---------------------------------------------------------------------------
function appendMessage(role, text, typing = false) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.textContent = role === "user" ? "You" : "AI";

  const content = document.createElement("div");
  content.className = "message-content";

  if (typing) {
    content.innerHTML = `<div class="typing-indicator"><span></span><span></span><span></span></div>`;
  } else if (text) {
    if (role === "agent") {
      renderMarkdown(content, text);
    } else {
      content.textContent = text;
    }
  }

  wrapper.appendChild(avatar);
  wrapper.appendChild(content);
  messagesEl.appendChild(wrapper);
  scrollToBottom();

  return wrapper;
}

function removeTypingIndicator(el) {
  const indicator = el.querySelector(".typing-indicator");
  if (indicator) {
    indicator.remove();
    // Clear leftover text that might have been the indicator
  }
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function autoResize(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = Math.min(textarea.scrollHeight, 150) + "px";
}

// ---------------------------------------------------------------------------
// Simple Markdown renderer (handles bold, code, tables, lists, headings)
// ---------------------------------------------------------------------------
function renderMarkdown(el, text) {
  if (!text) {
    el.innerHTML = "";
    return;
  }

  let html = escapeHtml(text);

  // Code blocks (```...```)
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre><code>${code.trim()}</code></pre>`;
  });

  // Inline code
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Italic
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

  // Headings (### / ## / #)
  html = html.replace(/^### (.+)$/gm, "<h4>$1</h4>");
  html = html.replace(/^## (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^# (.+)$/gm, "<h2>$1</h2>");

  // Simple table detection (pipe-delimited)
  html = html.replace(
    /^(\|.+\|)\n(\|[-| :]+\|)\n((?:\|.+\|\n?)+)/gm,
    (_, header, sep, body) => {
      const ths = header.split("|").filter(Boolean).map(c => `<th>${c.trim()}</th>`).join("");
      const rows = body.trim().split("\n").map(row => {
        const tds = row.split("|").filter(Boolean).map(c => `<td>${c.trim()}</td>`).join("");
        return `<tr>${tds}</tr>`;
      }).join("");
      return `<table><thead><tr>${ths}</tr></thead><tbody>${rows}</tbody></table>`;
    }
  );

  // Unordered lists
  html = html.replace(/^[•\-\*] (.+)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`);

  // Paragraphs (double newlines)
  html = html.replace(/\n{2,}/g, "</p><p>");
  html = `<p>${html}</p>`;

  // Clean up empty paragraphs around block elements
  html = html.replace(/<p>\s*(<(?:pre|table|ul|h[2-4]))/g, "$1");
  html = html.replace(/(<\/(?:pre|table|ul|h[2-4])>)\s*<\/p>/g, "$1");

  el.innerHTML = html;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// ---------------------------------------------------------------------------
// Conversation tracking (in-memory)
// ---------------------------------------------------------------------------
function trackConversation(userText, agentText) {
  let conv = conversations.find(c => c.id === currentConversationId);
  if (!conv) {
    conv = {
      id: currentConversationId,
      title: userText.slice(0, 40) + (userText.length > 40 ? "…" : ""),
      messages: [],
    };
    conversations.unshift(conv);
  }
  conv.messages.push({ role: "user", text: userText });
  conv.messages.push({ role: "agent", text: agentText });
  renderChatHistory();
}

function renderChatHistory() {
  chatHistoryEl.innerHTML = "";
  for (const conv of conversations) {
    const btn = document.createElement("button");
    btn.className = "chat-history-item" +
      (conv.id === currentConversationId ? " active" : "");
    btn.textContent = conv.title;
    btn.addEventListener("click", () => loadConversation(conv));
    chatHistoryEl.appendChild(btn);
  }
}

function loadConversation(conv) {
  currentConversationId = conv.id;
  renderMessages(conv.messages);
  renderChatHistory();
}

function renderMessages(messages) {
  messagesEl.innerHTML = "";
  if (messages.length === 0) {
    // Show welcome screen again
    messagesEl.innerHTML = `
      <div class="welcome-message">
        <div class="welcome-icon">🏗️</div>
        <h2>Welcome to CIMIC Project Advisor</h2>
        <p>I can help you with project performance insights, financial analysis, safety metrics, and procurement data.</p>
        <div class="suggestions">
          <button class="suggestion" data-prompt="What is CIMIC's LTIFR target for 2025?">📊 LTIFR target for 2025</button>
          <button class="suggestion" data-prompt="Calculate EVM metrics: budget AUD 450M, actual costs AUD 412M, planned value AUD 420M">💰 EVM calculation</button>
          <button class="suggestion" data-prompt="What cost variance threshold triggers a red flag on CIMIC projects?">🚩 Cost variance thresholds</button>
          <button class="suggestion" data-prompt="Summarise CIMIC's safety policy for subcontractor management">🦺 Safety policy summary</button>
        </div>
      </div>`;
    return;
  }
  for (const msg of messages) {
    appendMessage(msg.role, msg.text);
  }
}
