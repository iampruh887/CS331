import { useState, useEffect } from "react";
import "../styles/ScriptsSidebar.css";

const API_BASE_URL = "http://localhost:8000";

export function ScriptsSidebar() {
  const [isOpen, setIsOpen] = useState(false);
  const [scripts, setScripts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [scriptOutput, setScriptOutput] = useState(null);
  const [runningScript, setRunningScript] = useState(null);

  useEffect(() => {
    fetchScripts();
  }, []);

  const fetchScripts = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/scripts`);
      if (!response.ok) throw new Error("Failed to fetch scripts");
      const data = await response.json();
      setScripts(data.scripts);
    } catch (err) {
      console.error("Error fetching scripts:", err);
    }
  };

  const runScript = async (scriptName) => {
    setRunningScript(scriptName);
    setScriptOutput(null);

    try {
      const response = await fetch(`${API_BASE_URL}/scripts/${scriptName}/run`, {
        method: "POST",
      });

      if (!response.ok) throw new Error("Failed to run script");
      const data = await response.json();

      setScriptOutput({
        name: data.script_name,
        status: data.status,
        output: data.output,
        error: data.error,
      });
    } catch (err) {
      console.error("Error running script:", err);
      setScriptOutput({
        name: scriptName,
        status: "error",
        output: "",
        error: err.message,
      });
    } finally {
      setRunningScript(null);
    }
  };

  return (
    <>
      <button
        className="sidebar-toggle"
        onClick={() => setIsOpen(!isOpen)}
        title="Toggle Scripts Sidebar"
      >
        {isOpen ? ">" : "<"}
      </button>

      <aside className={`scripts-sidebar ${isOpen ? "open" : "closed"}`}>
        <div className="sidebar-header">
          <h2>Scripts</h2>
          <button
            className="close-btn"
            onClick={() => setIsOpen(false)}
            title="Close sidebar"
          >
            X
          </button>
        </div>

        <div className="scripts-list">
          {scripts.length === 0 ? (
            <p className="no-scripts">No approved scripts found</p>
          ) : (
            scripts.map((script) => (
              <div key={script.name} className="script-item">
                <div className="script-info">
                  <h3>{script.name}</h3>
                  <p className="script-desc">{script.description}</p>
                </div>
                <button
                  className="run-btn"
                  onClick={() => runScript(script.name)}
                  disabled={runningScript === script.name}
                >
                  {runningScript === script.name ? "Running..." : "Run"}
                </button>
              </div>
            ))
          )}
        </div>

        {scriptOutput && (
          <div className="output-section">
            <h3 className="output-title">Output: {scriptOutput.name}</h3>
            <div className={`output-box ${scriptOutput.status}`}>
              {scriptOutput.status === "success" ? (
                <pre className="output-text">{scriptOutput.output}</pre>
              ) : (
                <>
                  <pre className="output-text error">
                    {scriptOutput.error || scriptOutput.output}
                  </pre>
                </>
              )}
            </div>
            <button
              className="clear-output-btn"
              onClick={() => setScriptOutput(null)}
            >
              Clear
            </button>
          </div>
        )}
      </aside>
    </>
  );
}
