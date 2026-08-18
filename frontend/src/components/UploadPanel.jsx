import { useState, useRef, useEffect, useCallback } from "react";

const ALLOWED = [".wav", ".mp3", ".ogg"];

function isAllowed(name) {
  const ext = name.slice(name.lastIndexOf(".")).toLowerCase();
  return ALLOWED.includes(ext);
}

export default function UploadPanel({ onUpload, loading }) {
  const [files, setFiles] = useState([]);
  const [dragOver, setDragOver] = useState(false);
  const [rejected, setRejected] = useState([]);
  const depthRef = useRef(0);
  const inputRef = useRef(null);
  const rejectTimerRef = useRef(null);

  // Шаг 1: глобальный перехват — файл никогда не откроется в браузере
  useEffect(() => {
    const prevent = (e) => e.preventDefault();
    window.addEventListener("dragover", prevent);
    window.addEventListener("drop", prevent);
    return () => {
      window.removeEventListener("dragover", prevent);
      window.removeEventListener("drop", prevent);
    };
  }, []);

  const showRejected = useCallback((names) => {
    setRejected(names);
    clearTimeout(rejectTimerRef.current);
    rejectTimerRef.current = setTimeout(() => setRejected([]), 5000);
  }, []);

  const addFiles = useCallback((fileList) => {
    const valid = [];
    const bad = [];
    for (const f of fileList) {
      if (isAllowed(f.name)) {
        valid.push(f);
      } else {
        bad.push(f.name);
      }
    }
    if (valid.length > 0) {
      setFiles((prev) => [...prev, ...valid]);
    }
    if (bad.length > 0) {
      showRejected(bad);
    }
  }, [showRejected]);

  const removeFile = useCallback((index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  // Шаг 2: счётчик dragenter/dragleave — стабильная подсветка без мерцания
  const handleDragEnter = useCallback((e) => {
    e.preventDefault();
    depthRef.current += 1;
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    depthRef.current -= 1;
    if (depthRef.current <= 0) {
      depthRef.current = 0;
      setDragOver(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    depthRef.current = 0;
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files);
    }
  }, [addFiles]);

  const handleInputChange = useCallback((e) => {
    addFiles(e.target.files);
    e.target.value = "";
  }, [addFiles]);

  const handleSubmit = useCallback((e) => {
    e.preventDefault();
    if (files.length === 0) return;
    onUpload(files);
  }, [files, onUpload]);

  return (
    <form onSubmit={handleSubmit} className="upload-panel">
      <h2>Загрузка аудио</h2>

      <div
        className={`dropzone ${dragOver ? "dropzone-active" : ""}`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".wav,.mp3,.ogg"
          multiple
          onChange={handleInputChange}
          style={{ display: "none" }}
        />
        <span className="dropzone-text">
          {dragOver ? "Отпустите файлы" : "Перетащите файлы сюда или нажмите для выбора"}
        </span>
        <span className="dropzone-hint">.wav, .mp3, .ogg — до 20 МБ каждый</span>
      </div>

      {rejected.length > 0 && (
        <div className="rejected-msg">
          Не поддерживается: {rejected.join(", ")} (допустимы: .wav, .mp3, .ogg)
        </div>
      )}

      {files.length > 0 && (
        <div className="file-chips">
          {files.map((f, i) => (
            <span key={`${f.name}-${i}`} className="file-chip">
              {f.name}
              <button type="button" className="chip-remove" onClick={() => removeFile(i)}>
                ✕
              </button>
            </span>
          ))}
        </div>
      )}

      <button type="submit" disabled={files.length === 0 || loading}>
        {loading ? "Анализ..." : "Анализировать"}
      </button>
    </form>
  );
}
