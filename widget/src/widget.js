(function () {
  "use strict";

  var script =
    document.currentScript ||
    document.querySelector('script[data-agency-id][src*="widget.js"]');
  if (!script) return;

  var agencyId = script.getAttribute("data-agency-id");
  var widgetToken = script.getAttribute("data-widget-token") || "";
  var apiBase =
    script.getAttribute("data-api-base") ||
    new URL(script.src, window.location.href).origin + "/api/v1";

  if (!agencyId || !widgetToken) {
    console.warn("[AI TravelDesk Widget] Missing data-agency-id or data-widget-token.");
    return;
  }

  var storageKey = "aitd_widget_conv_" + agencyId;
  var state = {
    open: false,
    conversationId: window.localStorage.getItem(storageKey),
    config: {
      brand_name: "Travel Assistant",
      primary_color: "#0F172A",
      secondary_color: "#2563EB",
      agent_name: "AI Flight Consultant",
      welcome_message: "Hello! Where would you like to fly?",
      logo_url: null,
    },
    messages: [],
    loading: false,
  };

  function headers() {
    return {
      "Content-Type": "application/json",
      "X-Agency-ID": agencyId,
      "X-Widget-Token": widgetToken,
    };
  }

  function apiFetch(path, opts) {
    return fetch(apiBase + path, Object.assign({ headers: headers() }, opts || {})).then(
      function (res) {
        if (!res.ok) {
          throw new Error("Widget API error: " + res.status);
        }
        return res.json();
      }
    );
  }

  var root = document.createElement("div");
  root.id = "aitd-widget-root";
  root.style.cssText =
    "position:fixed;bottom:20px;right:20px;z-index:999999;font-family:system-ui,-apple-system,sans-serif;";
  document.body.appendChild(root);

  var launcher = document.createElement("button");
  launcher.type = "button";
  launcher.setAttribute("aria-label", "Open AI Flight Consultant");
  launcher.style.cssText =
    "width:56px;height:56px;border-radius:9999px;border:none;cursor:pointer;color:#fff;font-weight:600;font-size:14px;box-shadow:0 10px 25px rgba(0,0,0,0.2);display:flex;align-items:center;justify-content:center;";
  launcher.textContent = "Chat";

  var panel = document.createElement("div");
  panel.style.cssText =
    "display:none;width:min(380px,calc(100vw - 32px));height:min(540px,calc(100vh - 96px));background:#fff;color:#0f172a;border-radius:16px;border:1px solid #e2e8f0;box-shadow:0 20px 40px rgba(15,23,42,0.18);overflow:hidden;flex-direction:column;margin-bottom:12px;";

  var header = document.createElement("div");
  header.style.cssText =
    "padding:14px 16px;color:#fff;display:flex;align-items:center;justify-content:space-between;gap:10px;";

  var headerTitle = document.createElement("div");
  var brandEl = document.createElement("div");
  brandEl.style.cssText = "font-weight:600;font-size:14px;";
  var subEl = document.createElement("div");
  subEl.style.cssText = "font-size:11px;opacity:0.85;";
  headerTitle.appendChild(brandEl);
  headerTitle.appendChild(subEl);

  var closeBtn = document.createElement("button");
  closeBtn.type = "button";
  closeBtn.textContent = "✕";
  closeBtn.style.cssText =
    "background:transparent;border:none;color:#fff;font-size:16px;cursor:pointer;";
  closeBtn.onclick = function () {
    toggle(false);
  };
  header.appendChild(headerTitle);
  header.appendChild(closeBtn);

  var body = document.createElement("div");
  body.style.cssText =
    "flex:1;overflow-y:auto;padding:12px;background:#f8fafc;display:flex;flex-direction:column;gap:8px;";

  var form = document.createElement("form");
  form.style.cssText =
    "display:flex;gap:8px;padding:10px;border-top:1px solid #e2e8f0;background:#fff;";
  var input = document.createElement("input");
  input.type = "text";
  input.placeholder = "Ask in English, Bangla, or Banglish...";
  input.style.cssText =
    "flex:1;padding:8px 10px;border:1px solid #cbd5e1;border-radius:8px;font-size:13px;";
  var sendBtn = document.createElement("button");
  sendBtn.type = "submit";
  sendBtn.textContent = "Send";
  sendBtn.style.cssText =
    "padding:8px 14px;border:none;border-radius:8px;color:#fff;font-size:13px;font-weight:600;cursor:pointer;";

  form.appendChild(input);
  form.appendChild(sendBtn);

  var footerBar = document.createElement("div");
  footerBar.style.cssText =
    "padding:6px 12px;background:#fff;border-top:1px solid #f1f5f9;display:flex;justify-content:space-between;align-items:center;font-size:11px;color:#64748b;";
  var handoffBtn = document.createElement("button");
  handoffBtn.type = "button";
  handoffBtn.textContent = "Talk to Human Agent";
  handoffBtn.style.cssText =
    "background:none;border:none;color:#2563eb;cursor:pointer;font-size:11px;padding:0;font-weight:500;";
  handoffBtn.onclick = function () {
    sendText("Please connect me to a human agent");
  };
  var poweredEl = document.createElement("span");
  poweredEl.textContent = "AI TravelDesk";
  footerBar.appendChild(handoffBtn);
  footerBar.appendChild(poweredEl);

  panel.appendChild(header);
  panel.appendChild(body);
  panel.appendChild(form);
  panel.appendChild(footerBar);
  root.appendChild(panel);
  root.appendChild(launcher);

  function applyTheme() {
    var primary = state.config.primary_color || "#0F172A";
    var secondary = state.config.secondary_color || "#2563EB";
    header.style.background = primary;
    launcher.style.background = secondary;
    sendBtn.style.background = secondary;
    handoffBtn.style.color = secondary;
    brandEl.textContent = state.config.brand_name;
    subEl.textContent = state.config.agent_name;
  }

  function renderMessages() {
    body.innerHTML = "";
    state.messages.forEach(function (m) {
      var bubble = document.createElement("div");
      var isUser = m.sender_type === "CUSTOMER";
      bubble.style.cssText = isUser
        ? "align-self:flex-end;max-width:82%;padding:8px 12px;border-radius:12px;font-size:13px;white-space:pre-line;background:" +
          (state.config.secondary_color || "#2563EB") +
          ";color:#fff;"
        : "align-self:flex-start;max-width:85%;padding:8px 12px;border-radius:12px;font-size:13px;white-space:pre-line;background:#fff;border:1px solid #e2e8f0;color:#0f172a;";
      bubble.textContent = m.content;
      body.appendChild(bubble);
    });
    body.scrollTop = body.scrollHeight;
  }

  function ensureConversation() {
    if (state.conversationId) {
      return apiFetch("/widget/conversations/" + state.conversationId)
        .then(function (conv) {
          state.messages = conv.messages || [];
          renderMessages();
          return conv.id;
        })
        .catch(function () {
          state.conversationId = null;
          window.localStorage.removeItem(storageKey);
          return ensureConversation();
        });
    }
    return apiFetch("/widget/conversations", {
      method: "POST",
      body: JSON.stringify({ channel: "WIDGET" }),
    }).then(function (conv) {
      state.conversationId = conv.id;
      window.localStorage.setItem(storageKey, conv.id);
      state.messages = conv.messages || [];
      renderMessages();
      return conv.id;
    });
  }

  function sendText(text) {
    if (!text || state.loading) return;
    state.loading = true;
    input.value = "";
    ensureConversation()
      .then(function (convId) {
        return apiFetch("/widget/conversations/" + convId + "/messages", {
          method: "POST",
          body: JSON.stringify({ content: text }),
        });
      })
      .then(function (turn) {
        state.messages.push(turn.customer_message, turn.agent_message);
        renderMessages();
      })
      .catch(function (err) {
        state.messages.push({
          sender_type: "SYSTEM",
          content: "Unable to send message (" + err.message + ").",
        });
        renderMessages();
      })
      .finally(function () {
        state.loading = false;
      });
  }

  form.onsubmit = function (e) {
    e.preventDefault();
    sendText(input.value.trim());
  };

  function toggle(force) {
    state.open = typeof force === "boolean" ? force : !state.open;
    panel.style.display = state.open ? "flex" : "none";
    if (state.open && state.messages.length === 0) {
      ensureConversation();
    }
  }

  launcher.onclick = function () {
    toggle();
  };

  applyTheme();
  apiFetch("/widget/config")
    .then(function (cfg) {
      state.config = cfg;
      applyTheme();
    })
    .catch(function () {});
})();
