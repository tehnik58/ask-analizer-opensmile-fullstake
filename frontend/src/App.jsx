import { useState, useCallback } from "react";
import UploadPanel from "./components/UploadPanel";
import AudioPlayer from "./components/AudioPlayer";
import ConfidenceBadge from "./components/ConfidenceBadge";
import { uploadFiles, getResults } from "./api";
import "./App.css";

function App() {
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const poll = useCallback(async (sessionId) => {
    setPolling(true);
    const maxAttempts = 60;
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      try {
        const data = await getResults(sessionId);
        if (data.status === "done") {
          setResults(data);
          setPolling(false);
          return;
        }
        if (data.status === "error") {
          setError(data.error || "Analysis failed");
          setPolling(false);
          return;
        }
      } catch (e) {
        setError(e.message);
        setPolling(false);
        return;
      }
    }
    setError("Timeout waiting for results");
    setPolling(false);
  }, []);

  const handleUpload = async (original, translations) => {
    setError(null);
    setResults(null);
    setLoading(true);
    try {
      const { session_id } = await uploadFiles(original, translations);
      poll(session_id);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header>
        <h1>Translation Confidence Analyzer</h1>
      </header>

      <UploadPanel onUpload={handleUpload} loading={loading || polling} />

      {error && <div className="error">{error}</div>}

      {polling && <div className="status">Анализ выполняется...</div>}

      {results && (
        <div className="results">
          <section className="result-section">
            <h2>Оригинал</h2>
            <AudioPlayer src={results.original.audio_url} label="Original" />
          </section>

          {results.translations.map((tr, i) => (
            <section key={tr.id} className="result-section">
              <h2>
                Студент {i + 1} ({tr.id})
                <ConfidenceBadge score={tr.confidence_score} label={tr.confidence_label} />
              </h2>
              {tr.warning && <div className="warning">{tr.warning}</div>}
              <AudioPlayer src={tr.audio_url} label={tr.id} />
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;
