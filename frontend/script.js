/* ============================================================
   AI Voice Sales Agent — Phase 2 Client Logic
   ============================================================
   Milestones covered:
     1. Browser microphone (Web Speech API)
     2. Speech-to-text → transcript in UI
     3. POST /api/chat → backend (HTTP fallback)
     4. WS /ws/chat → backend (streaming, preferred)
     5. Display AI response (streaming token-by-token)
     6. Text-to-speech (SpeechSynthesis)
     7. Server-side conversation memory (via session_id)
     8. Session persistence across page reloads
     9. New conversation / clear history controls
    10. WebSocket auto-reconnection with HTTP fallback
   ============================================================ */

(function () {
    "use strict";

    // ── DOM refs ─────────────────────────────────────────────
    const $messages       = document.getElementById("conversation-messages");
    const $micBtn         = document.getElementById("mic-button");
    const $micIcon        = document.getElementById("mic-icon");
    const $stopIcon       = document.getElementById("stop-icon");
    const $micLabel       = document.getElementById("mic-label");
    const $statusBar      = document.getElementById("status-bar");
    const $statusText     = document.getElementById("status-text");
    const $connBadge      = document.getElementById("connection-status");
    const $overlay        = document.getElementById("unsupported-overlay");
    const $newChatBtn     = document.getElementById("new-chat-button");

    // ── State ────────────────────────────────────────────────
    let isListening  = false;
    let isSpeaking   = false;
    let recognition  = null;
    const synth      = window.speechSynthesis;

    // Session ID — persisted in sessionStorage so it survives page reloads
    // but not browser restarts (intentional: fresh session on new visit)
    const SESSION_KEY = "voice_agent_session_id";
    let sessionId = sessionStorage.getItem(SESSION_KEY) || null;

    // ── WebSocket state ─────────────────────────────────────
    let ws = null;
    let wsConnected = false;
    let wsReconnectTimer = null;
    const WS_RECONNECT_DELAY = 3000;

    // ── Feature detection ────────────────────────────────────
    const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        $overlay.classList.remove("overlay--hidden");
        $micBtn.disabled = true;
        return;
    }

    // ── Init recognition ─────────────────────────────────────
    function createRecognition() {
        const rec = new SpeechRecognition();
        rec.lang            = "en-US";
        rec.interimResults  = true;
        rec.continuous      = false;   // push-to-talk: single utterance
        rec.maxAlternatives = 1;

        rec.onstart = () => {
            isListening = true;
            setUIState("listening");
        };

        rec.onresult = (e) => {
            let interim = "";
            let final_  = "";

            for (let i = e.resultIndex; i < e.results.length; i++) {
                const transcript = e.results[i][0].transcript;
                if (e.results[i].isFinal) {
                    final_ += transcript;
                } else {
                    interim += transcript;
                }
            }

            // Update the live transcript bubble
            updateLiveTranscript(final_ || interim, !!final_);

            if (final_) {
                finishUserTurn(final_.trim());
            }
        };

        rec.onerror = (e) => {
            console.error("Speech recognition error:", e.error);
            isListening = false;

            if (e.error === "no-speech") {
                setUIState("idle");
                setStatus("No speech detected — try again");
            } else if (e.error === "aborted") {
                setUIState("idle");
            } else {
                setUIState("error");
                setStatus(`Error: ${e.error}`);
            }

            removeLiveTranscript();
        };

        rec.onend = () => {
            isListening = false;
            // Only reset if we haven't already transitioned
            if ($statusBar.classList.contains("listening")) {
                setUIState("idle");
            }
        };

        return rec;
    }

    // ── UI State machine ─────────────────────────────────────
    function setUIState(state) {
        $statusBar.className = "status-bar " + state;
        $micBtn.classList.toggle("recording", state === "listening");

        switch (state) {
            case "idle":
                showMicIcon(true);
                $micBtn.disabled = false;
                $micLabel.textContent = "Tap to speak";
                setStatus("Ready to listen");
                break;
            case "listening":
                showMicIcon(false);
                $micBtn.disabled = false;
                $micLabel.textContent = "Listening…";
                setStatus("Listening…");
                break;
            case "processing":
                showMicIcon(true);
                $micBtn.disabled = true;
                $micLabel.textContent = "Processing…";
                setStatus("Thinking…");
                break;
            case "speaking":
                showMicIcon(true);
                $micBtn.disabled = true;
                $micLabel.textContent = "Speaking…";
                setStatus("Speaking response…");
                break;
            case "error":
                showMicIcon(true);
                $micBtn.disabled = false;
                $micLabel.textContent = "Tap to retry";
                break;
        }
    }

    function showMicIcon(showMic) {
        $micIcon.classList.toggle("mic-btn__icon--hidden", !showMic);
        $stopIcon.classList.toggle("mic-btn__icon--hidden", showMic);
        // Ensure only one is displayed
        $micIcon.style.display  = showMic ? "" : "none";
        $stopIcon.style.display = showMic ? "none" : "";
    }

    function setStatus(text) {
        $statusText.textContent = text;
    }

    // ── Live transcript (interim bubble) ─────────────────────
    let $liveBubble = null;

    function updateLiveTranscript(text, isFinal) {
        if (!$liveBubble) {
            $liveBubble = addMessage("user", text, { live: true });
        }
        const p = $liveBubble.querySelector("p");
        if (p) p.textContent = text;
    }

    function removeLiveTranscript() {
        if ($liveBubble) {
            $liveBubble.remove();
            $liveBubble = null;
        }
    }

    // ── Message rendering ────────────────────────────────────
    function addMessage(role, text, options = {}) {
        const { live = false } = options;

        const wrapper = document.createElement("div");
        wrapper.className = `message message--${role === "user" ? "user" : "system"}`;
        if (live) wrapper.classList.add("message--live");

        const avatarSVG =
            role === "user"
                ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`
                : `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`;

        wrapper.innerHTML = `
            <div class="message__avatar message__avatar--${role === "user" ? "user" : "ai"}">
                ${avatarSVG}
            </div>
            <div class="message__content">
                <div class="message__bubble message__bubble--${role === "user" ? "user" : "ai"}">
                    <p>${escapeHTML(text)}</p>
                </div>
                <span class="message__time">${live ? "" : timeNow()}</span>
            </div>
        `;

        $messages.appendChild(wrapper);
        scrollToBottom();
        return wrapper;
    }

    function addTypingIndicator() {
        const wrapper = document.createElement("div");
        wrapper.className = "message message--system";
        wrapper.id = "typing-indicator";

        wrapper.innerHTML = `
            <div class="message__avatar message__avatar--ai">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            </div>
            <div class="message__content">
                <div class="message__bubble message__bubble--ai">
                    <div class="typing-indicator">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            </div>
        `;

        $messages.appendChild(wrapper);
        scrollToBottom();
        return wrapper;
    }

    function removeTypingIndicator() {
        const el = document.getElementById("typing-indicator");
        if (el) el.remove();
    }

    // ── Streaming message bubble ─────────────────────────────
    let $streamBubble = null;

    function addStreamingMessage() {
        const wrapper = document.createElement("div");
        wrapper.className = "message message--system";
        wrapper.id = "streaming-message";

        wrapper.innerHTML = `
            <div class="message__avatar message__avatar--ai">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            </div>
            <div class="message__content">
                <div class="message__bubble message__bubble--ai">
                    <p class="streaming-text"></p><span class="streaming-cursor">▎</span>
                </div>
            </div>
        `;

        $messages.appendChild(wrapper);
        scrollToBottom();
        $streamBubble = wrapper;
        return wrapper;
    }

    function updateStreamingMessage(text) {
        if (!$streamBubble) return;
        const p = $streamBubble.querySelector(".streaming-text");
        if (p) p.textContent = text;
        scrollToBottom();
    }

    function finalizeStreamingMessage(fullText) {
        if (!$streamBubble) return;
        const p = $streamBubble.querySelector(".streaming-text");
        if (p) p.textContent = fullText;

        // Remove the streaming cursor
        const cursor = $streamBubble.querySelector(".streaming-cursor");
        if (cursor) cursor.remove();

        // Add timestamp
        const content = $streamBubble.querySelector(".message__content");
        if (content) {
            const timeSpan = document.createElement("span");
            timeSpan.className = "message__time";
            timeSpan.textContent = timeNow();
            content.appendChild(timeSpan);
        }

        $streamBubble.removeAttribute("id");
        $streamBubble = null;
    }

    function removeStreamingMessage() {
        if ($streamBubble) {
            $streamBubble.remove();
            $streamBubble = null;
        }
        const el = document.getElementById("streaming-message");
        if (el) el.remove();
    }

    // ── Core flow ────────────────────────────────────────────

    /**
     * Called when the user finishes speaking (final transcript).
     */
    async function finishUserTurn(text) {
        // Replace the live bubble with a permanent one
        removeLiveTranscript();
        addMessage("user", text);

        setUIState("processing");

        try {
            let reply, sid;

            if (wsConnected && ws && ws.readyState === WebSocket.OPEN) {
                // ── WebSocket path (streaming) ──────────────
                const result = await sendViaWebSocket(text);
                reply = result.reply;
                sid = result.session_id;
            } else {
                // ── HTTP fallback path ──────────────────────
                const typingEl = addTypingIndicator();
                const result = await sendToBackend(text);
                removeTypingIndicator();
                addMessage("ai", result.reply);
                reply = result.reply;
                sid = result.session_id;
            }

            // Persist the session ID for future requests
            if (sid) {
                sessionId = sid;
                sessionStorage.setItem(SESSION_KEY, sid);
            }

            // Speak the response
            await speakText(reply);
        } catch (err) {
            removeTypingIndicator();
            removeStreamingMessage();
            addMessage("ai", "Sorry, I couldn't process that. Please try again.");
            console.error("Backend error:", err);
        }

        setUIState("idle");
    }

    // ── WebSocket communication ──────────────────────────────

    function connectWebSocket() {
        if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
            return; // already connected or connecting
        }

        const protocol = location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${location.host}/ws/chat`;

        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            wsConnected = true;
            console.log("[WS] Connected — streaming enabled");
            updateConnectionBadge("live");
            if (wsReconnectTimer) {
                clearTimeout(wsReconnectTimer);
                wsReconnectTimer = null;
            }
        };

        ws.onclose = () => {
            wsConnected = false;
            console.log("[WS] Disconnected — falling back to HTTP");
            updateConnectionBadge("online");
            // Schedule reconnection
            if (!wsReconnectTimer) {
                wsReconnectTimer = setTimeout(() => {
                    wsReconnectTimer = null;
                    connectWebSocket();
                }, WS_RECONNECT_DELAY);
            }
        };

        ws.onerror = (e) => {
            console.warn("[WS] Error:", e);
            // onclose will fire after this
        };
    }

    /**
     * Send a message via WebSocket and stream the response.
     * Returns a Promise that resolves when streaming is complete.
     */
    function sendViaWebSocket(message) {
        return new Promise((resolve, reject) => {
            if (!ws || ws.readyState !== WebSocket.OPEN) {
                reject(new Error("WebSocket not connected"));
                return;
            }

            let fullReply = "";

            const handler = (e) => {
                let data;
                try {
                    data = JSON.parse(e.data);
                } catch {
                    return;
                }

                if (data.type === "stream_start") {
                    addStreamingMessage();
                } else if (data.type === "token") {
                    fullReply += data.content;
                    updateStreamingMessage(fullReply);
                } else if (data.type === "stream_end") {
                    ws.removeEventListener("message", handler);
                    finalizeStreamingMessage(data.full_reply || fullReply);
                    resolve({
                        reply: data.full_reply || fullReply,
                        session_id: data.session_id || null,
                    });
                } else if (data.type === "error") {
                    ws.removeEventListener("message", handler);
                    removeStreamingMessage();
                    reject(new Error(data.message || "WebSocket error"));
                }
            };

            ws.addEventListener("message", handler);

            ws.send(JSON.stringify({
                type: "message",
                message: message,
                session_id: sessionId,
            }));
        });
    }

    /**
     * POST /api/chat — HTTP fallback (original Phase 1 path)
     */
    async function sendToBackend(message) {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message,
                session_id: sessionId,
            }),
        });

        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }

        const data = await res.json();
        return {
            reply: data.reply || "No response from the agent.",
            session_id: data.session_id || null,
        };
    }

    // ── Text-to-Speech ───────────────────────────────────────
    function speakText(text) {
        return new Promise((resolve) => {
            if (!synth) {
                resolve();
                return;
            }

            // Cancel any ongoing speech
            synth.cancel();

            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang  = "en-US";
            utterance.rate  = 1.0;
            utterance.pitch = 1.0;

            // Try to pick a nice voice
            const voices = synth.getVoices();
            const preferred = voices.find(
                (v) => v.name.includes("Google") && v.lang.startsWith("en")
            ) || voices.find((v) => v.lang.startsWith("en"));

            if (preferred) utterance.voice = preferred;

            utterance.onstart = () => {
                isSpeaking = true;
                setUIState("speaking");
            };

            utterance.onend = () => {
                isSpeaking = false;
                resolve();
            };

            utterance.onerror = (e) => {
                console.error("TTS error:", e);
                isSpeaking = false;
                resolve();
            };

            synth.speak(utterance);
        });
    }

    // ── Mic button handler ───────────────────────────────────
    $micBtn.addEventListener("click", () => {
        if (isListening) {
            // Stop recording
            recognition.stop();
            isListening = false;
            setUIState("idle");
            return;
        }

        // Cancel any ongoing speech when user wants to talk
        if (isSpeaking) {
            synth.cancel();
            isSpeaking = false;
        }

        // Start recording
        recognition = createRecognition();
        try {
            recognition.start();
        } catch (err) {
            console.error("Could not start recognition:", err);
            setUIState("error");
            setStatus("Microphone access denied");
        }
    });

    // ── New Chat button handler ──────────────────────────────
    if ($newChatBtn) {
        $newChatBtn.addEventListener("click", async () => {
            // Clear the UI
            $messages.innerHTML = "";

            // Delete the old session on the server (fire & forget)
            if (sessionId) {
                fetch(`/api/session/${sessionId}`, { method: "DELETE" }).catch(() => {});
            }

            // Clear the stored session
            sessionId = null;
            sessionStorage.removeItem(SESSION_KEY);

            setStatus("New conversation started");

            // Add a welcome-back message
            addMessage("ai", "Hello! I'm your AI sales assistant. How can I help you today?");
        });
    }

    // ── Restore session on load ──────────────────────────────
    async function restoreSession() {
        if (!sessionId) return;

        try {
            const res = await fetch(`/api/session/${sessionId}/history`);
            if (!res.ok) {
                // Session expired or not found — start fresh
                sessionId = null;
                sessionStorage.removeItem(SESSION_KEY);
                return;
            }

            const data = await res.json();
            if (data.turns && data.turns.length > 0) {
                // Replay the conversation into the UI
                for (const turn of data.turns) {
                    // Skip summary/context turns from pruning
                    if (turn.content.startsWith("[Earlier conversation context")) {
                        continue;
                    }
                    addMessage(
                        turn.role === "assistant" ? "ai" : "user",
                        turn.content
                    );
                }
                setStatus(`Session restored — ${data.turn_count} messages`);
            }
        } catch (err) {
            console.warn("Could not restore session:", err);
            sessionId = null;
            sessionStorage.removeItem(SESSION_KEY);
        }
    }

    // ── Connection badge ─────────────────────────────────────
    function updateConnectionBadge(state) {
        const $text = $connBadge.querySelector(".status-badge__text");
        switch (state) {
            case "live":
                $connBadge.className = "status-badge status-badge--live";
                $text.textContent = "Live";
                break;
            case "online":
                $connBadge.className = "status-badge status-badge--online";
                $text.textContent = "Online";
                break;
            case "offline":
                $connBadge.className = "status-badge status-badge--offline";
                $text.textContent = "Offline";
                break;
        }
    }

    // ── Helpers ──────────────────────────────────────────────
    function escapeHTML(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    function timeNow() {
        return new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    function scrollToBottom() {
        const container = document.getElementById("conversation-container");
        requestAnimationFrame(() => {
            container.scrollTop = container.scrollHeight;
        });
    }

    // ── Health check on load ─────────────────────────────────
    async function checkBackend() {
        try {
            const res = await fetch("/health");
            if (res.ok) {
                // Don't downgrade from "Live" to "Online" if WS is connected
                if (!wsConnected) {
                    updateConnectionBadge("online");
                }
            } else {
                throw new Error();
            }
        } catch {
            if (!wsConnected) {
                updateConnectionBadge("offline");
            }
        }
    }

    // Load voices (Chrome loads them async)
    if (synth) {
        synth.getVoices();
        synth.addEventListener("voiceschanged", () => synth.getVoices());
    }

    // Initial state
    setUIState("idle");
    checkBackend();
    restoreSession();
    connectWebSocket();

    // Re-check backend every 30s
    setInterval(checkBackend, 30000);
})();
