/* ════════════════════════════════════════════════
   J.A.R.V.I.S. – Client-Side Application Logic
   ════════════════════════════════════════════════ */

(() => {
    "use strict";

    // ── DOM refs ──
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const consoleOutput = $("#console-output");
    const commandForm = $("#command-form");
    const commandInput = $("#command-input");
    const quickActions = $$("#quick-actions .action-card");
    const musicLibrary = $("#music-library");
    const newsFeed = $("#news-feed");
    const historyFeed = $("#history-feed");
    const refreshNews = $("#refresh-news");
    const clockEl = $("#clock");

    // ── WebSocket ──
    let ws = null;

    function connectWS() {
        const protocol = location.protocol === "https:" ? "wss" : "ws";
        ws = new WebSocket(`${protocol}://${location.host}/ws`);

        ws.onopen = () => {
            console.log("[WS] Connected");
        };

        ws.onmessage = (event) => {
            const payload = JSON.parse(event.data);
            if (payload.event === "command_result") {
                renderBotMessage(payload.data);
            }
        };

        ws.onclose = () => {
            console.log("[WS] Disconnected – reconnecting in 3s…");
            setTimeout(connectWS, 3000);
        };
    }

    // ── Clock ──
    function updateClock() {
        const now = new Date();
        clockEl.textContent = now.toLocaleTimeString("en-IN", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: true,
        });
    }
    setInterval(updateClock, 1000);
    updateClock();

    // ── Send Command ──
    async function sendCommand(cmd) {
        if (!cmd.trim()) return;
        clearWelcome();
        renderUserMessage(cmd);

        // Show loading
        const loadingId = showLoading();

        try {
            const res = await fetch("/api/command", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ command: cmd }),
            });
            const data = await res.json();
            removeLoading(loadingId);
            renderBotMessage(data);
            addHistory(cmd, data);

            // If news, also update sidebar
            if (data.type === "news" && data.articles) {
                renderNewsFeed(data.articles);
            }
        } catch (err) {
            removeLoading(loadingId);
            renderBotMessage({
                type: "error",
                status: "error",
                message: "Connection error. Is the server running?",
                timestamp: new Date().toLocaleTimeString(),
            });
        }
    }

    // ── Render functions ──
    function clearWelcome() {
        const welcome = consoleOutput.querySelector(".welcome-message");
        if (welcome) {
            welcome.style.animation = "fadeIn 0.3s ease reverse forwards";
            setTimeout(() => welcome.remove(), 300);
        }
    }

    function renderUserMessage(text) {
        const div = document.createElement("div");
        div.className = "msg user-msg";
        div.innerHTML = `
            <div class="msg-bubble">
                <div>${escapeHtml(text)}</div>
                <div class="msg-meta">
                    <span>${new Date().toLocaleTimeString()}</span>
                </div>
            </div>
        `;
        consoleOutput.appendChild(div);
        scrollToBottom();
    }

    function renderBotMessage(data) {
        const div = document.createElement("div");
        div.className = "msg bot-msg";

        let content = `<div>${escapeHtml(data.message)}</div>`;

        // News articles
        if (data.type === "news" && data.articles) {
            content += `<div class="news-cards">`;
            data.articles.forEach((a) => {
                if (a.title) {
                    content += `
                        <a class="news-card-inline" href="${escapeHtml(a.url)}" target="_blank" rel="noopener">
                            <div class="news-title-inline">${escapeHtml(a.title)}</div>
                            <div class="news-source-inline">${escapeHtml(a.source)}</div>
                        </a>`;
                }
            });
            content += `</div>`;
        }

        // Help commands
        if (data.type === "help" && data.commands) {
            content += `<table class="help-table">`;
            data.commands.forEach((c) => {
                content += `<tr><td>${escapeHtml(c.cmd)}</td><td>${escapeHtml(c.desc)}</td></tr>`;
            });
            content += `</table>`;
        }

        // URL link
        if (data.url) {
            content += `<div style="margin-top:0.4rem;"><a href="${escapeHtml(data.url)}" target="_blank" rel="noopener" style="color:var(--accent);font-size:0.75rem;font-family:var(--font-mono);text-decoration:none;opacity:0.7;">${escapeHtml(data.url)}</a></div>`;
        }

        const statusClass = data.status || "info";

        div.innerHTML = `
            <div class="msg-bubble">
                ${content}
                <div class="msg-meta">
                    <span class="msg-status ${statusClass}">${statusClass.toUpperCase()}</span>
                    <span>${data.timestamp || new Date().toLocaleTimeString()}</span>
                </div>
            </div>
        `;
        consoleOutput.appendChild(div);
        scrollToBottom();
    }

    let loadingCounter = 0;

    function showLoading() {
        const id = `loading-${++loadingCounter}`;
        const div = document.createElement("div");
        div.className = "msg bot-msg";
        div.id = id;
        div.innerHTML = `
            <div class="msg-bubble">
                <div class="loading-dots"><span></span><span></span><span></span></div>
            </div>
        `;
        consoleOutput.appendChild(div);
        scrollToBottom();
        return id;
    }

    function removeLoading(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function scrollToBottom() {
        requestAnimationFrame(() => {
            consoleOutput.scrollTop = consoleOutput.scrollHeight;
        });
    }

    // ── History ──
    function addHistory(cmd, data) {
        const item = document.createElement("div");
        item.className = "history-item";
        item.innerHTML = `
            <div class="history-dot ${data.status || "info"}"></div>
            <span class="history-cmd">${escapeHtml(cmd)}</span>
            <span class="history-time">${data.timestamp || ""}</span>
        `;
        item.addEventListener("click", () => {
            commandInput.value = cmd;
            commandInput.focus();
        });
        historyFeed.prepend(item);

        // Keep max 30
        while (historyFeed.children.length > 30) {
            historyFeed.lastChild.remove();
        }
    }

    // ── Music library ──
    async function loadMusicLibrary() {
        try {
            const res = await fetch("/api/music");
            const data = await res.json();
            musicLibrary.innerHTML = "";
            data.music.forEach((m) => {
                const item = document.createElement("div");
                item.className = "music-item";
                item.innerHTML = `
                    <div class="music-play">
                        <svg viewBox="0 0 24 24"><polygon points="5,3 19,12 5,21"/></svg>
                    </div>
                    <span class="music-name">${escapeHtml(m.name)}</span>
                `;
                item.addEventListener("click", () => sendCommand(`play ${m.name}`));
                musicLibrary.appendChild(item);
            });
        } catch (err) {
            musicLibrary.innerHTML = `<div style="color:var(--text-muted);font-size:0.8rem;padding:0.5rem;">Could not load music library.</div>`;
        }
    }

    // ── News sidebar ──
    function renderNewsFeed(articles) {
        newsFeed.innerHTML = "";
        articles.forEach((a) => {
            if (!a.title) return;
            const card = document.createElement("a");
            card.className = "news-card";
            card.href = a.url;
            card.target = "_blank";
            card.rel = "noopener";
            card.innerHTML = `
                <div class="news-source">${escapeHtml(a.source)}</div>
                <div class="news-title">${escapeHtml(a.title)}</div>
                ${a.description ? `<div class="news-desc">${escapeHtml(a.description)}</div>` : ""}
            `;
            newsFeed.appendChild(card);
        });
    }

    // ── Utility ──
    function escapeHtml(str) {
        if (!str) return "";
        const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
        return str.replace(/[&<>"']/g, (c) => map[c]);
    }

    // ══════════════════════════════
    //  Event Listeners
    // ══════════════════════════════

    // Form submit
    commandForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const cmd = commandInput.value.trim();
        if (cmd) {
            sendCommand(cmd);
            commandInput.value = "";
        }
    });

    // Quick action buttons
    quickActions.forEach((btn) => {
        btn.addEventListener("click", () => {
            const cmd = btn.dataset.cmd;
            if (cmd) sendCommand(cmd);
        });
    });

    // Welcome hint clicks
    document.addEventListener("click", (e) => {
        if (e.target.closest(".welcome-hints code")) {
            const cmd = e.target.textContent.trim();
            commandInput.value = cmd;
            commandInput.focus();
        }
    });

    // Refresh news
    refreshNews.addEventListener("click", () => sendCommand("news"));

    // ── Keyboard shortcuts ──
    document.addEventListener("keydown", (e) => {
        // Focus input on / key
        if (e.key === "/" && document.activeElement !== commandInput) {
            e.preventDefault();
            commandInput.focus();
        }
        // Escape to blur
        if (e.key === "Escape") {
            commandInput.blur();
        }
    });

    // ── Init ──
    loadMusicLibrary();
    connectWS();
})();
