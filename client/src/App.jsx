import { useState, useEffect, useRef } from "react";
import "./App.css";
import { ScriptsSidebar } from "./components/ScriptsSidebar";

const API_BASE_URL = "http://localhost:8000";

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesRef = useRef(null);
  const isAtBottomRef = useRef(true);
  const [showScrollDown, setShowScrollDown] = useState(false);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg = { role: "user", text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: text }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      const botMsg = { role: "assistant", text: data.reply };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      console.error("Chat error:", err);
      const errorMsg = {
        role: "assistant",
        text: "Sorry, I encountered an error. Please try again.",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-scroll 
  useEffect(() => {
    const el = messagesRef.current;
    if (!el) return;

    if (isAtBottomRef.current) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, [messages]);

  const handleMessagesScroll = () => {
    const el = messagesRef.current;
    if (!el) return;

    const atBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight < 60;

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

  return (
    <div className="app">
      <ScriptsSidebar />
      <main className="chat-container">
        <header className="app-header engine-card">
          <h1>Nexus Chatbot</h1>
          <p>Ask about time, system metrics, or anything else.</p>
          <p className="app-subtitle">
            Powered by a local parsing engine with tools for time and system
            metrics.
          </p>
        </header>

        <div
          className="messages"
          ref={messagesRef}
          onScroll={handleMessagesScroll}
        >
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`message ${m.role === "user" ? "user" : "assistant"}`}
            >
              <div className="bubble">{m.text}</div>
            </div>
          ))}
          {loading && <div className="status">Thinking…</div>}
        </div>

        {showScrollDown && (
          <button className="scroll-down-btn" onClick={scrollToBottom}>
            ↓ Scroll to latest
          </button>
        )}

        <div className="input-row">
          <input
            className="input"
            placeholder="Type your query..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button className="send-btn" onClick={handleSend} disabled={loading}>
            Send
          </button>
        </div>
      </main>
    </div>
  );
}

export default App;