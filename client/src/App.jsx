import { useEffect, useMemo, useRef, useState } from "react";
import "./App.css";

const AUTH_API_BASE =
  import.meta.env.VITE_AUTH_API_BASE || "http://127.0.0.1:8000";
const CHAT_API_BASE =
  import.meta.env.VITE_CHAT_API_BASE || "http://127.0.0.1:8001";

const QUICK_INTENTS = [
  "Show current system metrics",
  "What time is it right now?",
  "Schedule a reminder for 20 minutes from now",
  "Summarize the last response in two bullets",
];

const WRITE_ACTION_REGEX =
  /\b(restart|shutdown|delete|remove|drop|kill|write|register\s+script)\b/i;

const buildId = () => {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

const formatTime = (isoTime) => {
  try {
    return new Date(isoTime).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "--:--";
  }
};

const maskSensitiveOutput = (text) => {
  if (!text) return "";

  return text
    .replace(/AIza[0-9A-Za-z_-]{20,}/g, "[masked-api-key]")
    .replace(/sk-[A-Za-z0-9]{20,}/g, "[masked-secret]")
    .replace(/(api[_-]?key\s*[:=]\s*)([^\s]+)/gi, "$1[masked]");
};

const normalizeError = (error) => {
  const message = error?.message || "Unknown error";
  const lower = message.toLowerCase();

  if (lower.includes("gemini_api_key")) {
    return "Chat service is up but Gemini is not configured yet. Add GEMINI_API_KEY in chat/.env.";
  }
  if (lower.includes("failed to fetch") || lower.includes("network")) {
    return "A backend service is currently unavailable. Please try again in a few seconds.";
  }
  if (lower.includes("timed out")) {
    return "The request timed out. Please try a shorter prompt.";
  }
  return message;
};

async function requestJson(url, options = {}, timeoutMs = 20000) {
  const controller = new AbortController();
  const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });

    const rawText = await response.text();
    const payload = rawText ? JSON.parse(rawText) : {};

    if (!response.ok) {
      throw new Error(payload.detail || `Request failed with status ${response.status}`);
    }

    return payload;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Request timed out");
    }
    if (error instanceof SyntaxError) {
      throw new Error("Received non-JSON response from backend");
    }
    throw error;
  } finally {
    clearTimeout(timeoutHandle);
  }
}

function App() {
  const [authMode, setAuthMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [authToken, setAuthToken] = useState(
    () => localStorage.getItem("nexus_access_token") || ""
  );
  const [userEmail, setUserEmail] = useState(
    () => localStorage.getItem("nexus_user_email") || ""
  );
  const [userRole, setUserRole] = useState(
    () => localStorage.getItem("nexus_user_role") || "GENERAL"
  );

  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");

  const [messages, setMessages] = useState([
    {
      id: buildId(),
      role: "assistant",
      text: "Welcome to Nexus. Sign in and submit a command to begin task execution.",
      createdAt: new Date().toISOString(),
    },
  ]);
  const [input, setInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  const [services, setServices] = useState({
    auth: "checking",
    chat: "checking",
    chatModel: "--",
  });

  const [showScrollDown, setShowScrollDown] = useState(false);

  const messagesRef = useRef(null);
  const inputRef = useRef(null);
  const isAtBottomRef = useRef(true);

  const contextWindow = useMemo(() => {
    return messages.filter((entry) => entry.role === "user").slice(-3);
  }, [messages]);

  const setSession = (token, profile) => {
    setAuthToken(token);
    setUserEmail(profile?.email || "");
    setUserRole(profile?.role || "GENERAL");

    localStorage.setItem("nexus_access_token", token);
    localStorage.setItem("nexus_user_email", profile?.email || "");
    localStorage.setItem("nexus_user_role", profile?.role || "GENERAL");
  };

  const clearSession = () => {
    setAuthToken("");
    setUserEmail("");
    setUserRole("GENERAL");
    localStorage.removeItem("nexus_access_token");
    localStorage.removeItem("nexus_user_email");
    localStorage.removeItem("nexus_user_role");
  };

  const fetchCurrentUser = async (token) => {
    const profile = await requestJson(
      `${AUTH_API_BASE}/me`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
      10000
    );

    setUserEmail(profile.email || "");
    setUserRole(profile.role || "GENERAL");
    localStorage.setItem("nexus_user_email", profile.email || "");
    localStorage.setItem("nexus_user_role", profile.role || "GENERAL");

    return profile;
  };

  const loginWithPassword = async (nextEmail, nextPassword) => {
    const tokenData = await requestJson(
      `${AUTH_API_BASE}/login`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: nextEmail,
          password: nextPassword,
        }),
      },
      15000
    );

    const profile = await fetchCurrentUser(tokenData.access_token);
    setSession(tokenData.access_token, profile);
  };

  const registerThenLogin = async (nextEmail, nextPassword) => {
    await requestJson(
      `${AUTH_API_BASE}/register`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: nextEmail,
          password: nextPassword,
        }),
      },
      15000
    );

    await loginWithPassword(nextEmail, nextPassword);
  };

  const refreshServiceHealth = async () => {
    const nextState = {
      auth: "down",
      chat: "down",
      chatModel: "--",
    };

    try {
      await requestJson(`${AUTH_API_BASE}/`, {}, 5000);
      nextState.auth = "up";
    } catch {
      nextState.auth = "down";
    }

    try {
      const chatHealth = await requestJson(`${CHAT_API_BASE}/`, {}, 5000);
      nextState.chat = "up";
      nextState.chatModel = chatHealth.model || "--";
    } catch {
      nextState.chat = "down";
      nextState.chatModel = "--";
    }

    setServices(nextState);
  };

  useEffect(() => {
    refreshServiceHealth();
    const timer = setInterval(refreshServiceHealth, 15000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!authToken || userEmail) return;

    fetchCurrentUser(authToken).catch(() => {
      clearSession();
      setAuthError("Session expired. Please sign in again.");
    });
  }, [authToken, userEmail]);

  useEffect(() => {
    const el = messagesRef.current;
    if (!el || !isAtBottomRef.current) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, chatLoading]);

  const handleMessagesScroll = () => {
    const el = messagesRef.current;
    if (!el) return;

    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 72;
    isAtBottomRef.current = atBottom;
    setShowScrollDown(!atBottom);
  };

  const scrollToBottom = () => {
    const el = messagesRef.current;
    if (!el) return;

    isAtBottomRef.current = true;
    setShowScrollDown(false);
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  };

  const handleAuthSubmit = async (event) => {
    event.preventDefault();
    if (authLoading) return;

    const nextEmail = email.trim();
    const nextPassword = password.trim();
    if (!nextEmail || !nextPassword) {
      setAuthError("Email and password are required.");
      return;
    }

    setAuthLoading(true);
    setAuthError("");

    try {
      if (authMode === "register") {
        await registerThenLogin(nextEmail, nextPassword);
      } else {
        await loginWithPassword(nextEmail, nextPassword);
      }
      setPassword("");
    } catch (error) {
      clearSession();
      setAuthError(normalizeError(error));
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    clearSession();
    setAuthError("");
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || chatLoading) return;
    if (!authToken) {
      setAuthError("Authenticate first to access task execution features.");
      return;
    }

    if (WRITE_ACTION_REGEX.test(text)) {
      const approved = window.confirm(
        "This looks like a write-action command. Continue with execution request?"
      );
      if (!approved) {
        setMessages((prev) => [
          ...prev,
          {
            id: buildId(),
            role: "system",
            text: "Write-action request cancelled before execution.",
            createdAt: new Date().toISOString(),
          },
        ]);
        return;
      }
    }

    const userMessage = {
      id: buildId(),
      role: "user",
      text,
      createdAt: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setChatLoading(true);

    const startedAt = performance.now();

    try {
      const data = await requestJson(
        `${CHAT_API_BASE}/chat`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${authToken}`,
          },
          body: JSON.stringify({ message: text }),
        },
        45000
      );

      const latencyMs = Math.round(performance.now() - startedAt);
      const cleanedReply = maskSensitiveOutput(data.reply || "");
      const assistantReply = cleanedReply
        ? cleanedReply
        : "I did not understand that command, please try rephrasing it.";

      setMessages((prev) => [
        ...prev,
        {
          id: buildId(),
          role: "assistant",
          text: assistantReply,
          createdAt: new Date().toISOString(),
          latencyMs,
        },
      ]);
    } catch (error) {
      const fallbackMessage = normalizeError(error);
      setMessages((prev) => [
        ...prev,
        {
          id: buildId(),
          role: "assistant",
          text: fallbackMessage,
          createdAt: new Date().toISOString(),
        },
      ]);
    } finally {
      setChatLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleComposerKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="app-shell">
      <div className="ambient-glow" aria-hidden="true" />

      <main className="layout">
        <header className="hero card">
          <div>
            <p className="eyebrow">Nexus Intelligent Task Assistant</p>
            <h1>Command Center</h1>
            <p className="hero-subtitle">
              Authenticated chat interface for intent-driven task requests, with
              confirmation for risky actions and graceful fallback handling.
            </p>
          </div>
          <div className="service-row">
            <span className={`service-pill ${services.auth}`}>
              Auth API: {services.auth}
            </span>
            <span className={`service-pill ${services.chat}`}>
              Chat API: {services.chat}
            </span>
            <span className="service-pill neutral">Model: {services.chatModel}</span>
            <button className="refresh-btn" onClick={refreshServiceHealth}>
              Refresh Health
            </button>
          </div>
        </header>

        <div className="workspace">
          <aside className="left-rail">
            <section className="card panel">
              <h2>Authentication</h2>
              <p className="panel-note">
                Email/password authentication is required before task execution.
              </p>

              {authToken ? (
                <div className="signed-in-box">
                  <div>
                    <p className="label">Signed in user</p>
                    <p className="value">{userEmail || "Loading profile..."}</p>
                  </div>
                  <div>
                    <p className="label">Role</p>
                    <p className="value">{userRole}</p>
                  </div>
                  <button className="secondary-btn" onClick={handleLogout}>
                    Sign out
                  </button>
                </div>
              ) : (
                <>
                  <div className="mode-toggle" role="tablist" aria-label="Auth mode">
                    <button
                      type="button"
                      className={authMode === "login" ? "active" : ""}
                      onClick={() => setAuthMode("login")}
                    >
                      Sign in
                    </button>
                    <button
                      type="button"
                      className={authMode === "register" ? "active" : ""}
                      onClick={() => setAuthMode("register")}
                    >
                      Register
                    </button>
                  </div>

                  <form className="auth-form" onSubmit={handleAuthSubmit}>
                    <label>
                      Email
                      <input
                        type="email"
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                        placeholder="user@example.com"
                        autoComplete="email"
                        required
                      />
                    </label>

                    <label>
                      Password
                      <input
                        type="password"
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                        placeholder="At least 8 characters"
                        autoComplete={
                          authMode === "register" ? "new-password" : "current-password"
                        }
                        required
                      />
                    </label>

                    <button className="primary-btn" type="submit" disabled={authLoading}>
                      {authLoading
                        ? "Working..."
                        : authMode === "register"
                          ? "Create account"
                          : "Sign in"}
                    </button>
                  </form>

                  {authError && <p className="error-text">{authError}</p>}
                </>
              )}
            </section>

            <section className="card panel">
              <h2>Quick Intents</h2>
              <p className="panel-note">
                Based on SRS use-cases: metrics, scheduling, reminders, and command
                execution.
              </p>
              <div className="quick-grid">
                {QUICK_INTENTS.map((intent) => (
                  <button
                    key={intent}
                    className="intent-chip"
                    onClick={() => {
                      setInput(intent);
                      inputRef.current?.focus();
                    }}
                  >
                    {intent}
                  </button>
                ))}
              </div>
            </section>

            <section className="card panel">
              <h2>Context Memory</h2>
              <p className="panel-note">Last 3 user commands (context window)</p>
              <ol className="context-list">
                {contextWindow.length === 0 && <li>No commands sent in this session.</li>}
                {contextWindow.map((item) => (
                  <li key={item.id}>{item.text}</li>
                ))}
              </ol>
            </section>
          </aside>

          <section className="chat-panel card">
            <div className="chat-header">
              <h2>Task Chat Interface</h2>
              <p>
                Read-only tasks execute immediately. Write-action commands require
                confirmation before sending.
              </p>
            </div>

            <div className="messages" ref={messagesRef} onScroll={handleMessagesScroll}>
              {messages.map((entry) => (
                <article key={entry.id} className={`message ${entry.role}`}>
                  <div className="meta">
                    <span className="role-tag">{entry.role.toUpperCase()}</span>
                    <span>{formatTime(entry.createdAt)}</span>
                    {entry.latencyMs ? <span>{entry.latencyMs} ms</span> : null}
                  </div>
                  <div className="bubble">{entry.text}</div>
                </article>
              ))}

              {chatLoading && (
                <article className="message assistant">
                  <div className="meta">
                    <span className="role-tag">ASSISTANT</span>
                  </div>
                  <div className="bubble">Parsing intent and generating response...</div>
                </article>
              )}
            </div>

            {showScrollDown && (
              <button className="scroll-down-btn" onClick={scrollToBottom}>
                Jump to latest
              </button>
            )}

            <div className="composer">
              <textarea
                ref={inputRef}
                className="composer-input"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleComposerKeyDown}
                placeholder={
                  authToken
                    ? "Type a command, question, or schedule request..."
                    : "Sign in to unlock command execution"
                }
                disabled={!authToken || chatLoading}
                rows={2}
              />
              <div className="composer-actions">
                <button
                  className="secondary-btn"
                  onClick={() => setMessages([])}
                  disabled={chatLoading}
                >
                  Clear Chat
                </button>
                <button
                  className="primary-btn"
                  onClick={handleSend}
                  disabled={!authToken || chatLoading || !input.trim()}
                >
                  Send
                </button>
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

export default App;