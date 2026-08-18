import { useState, useRef } from "react";

const ALLOWED = [".wav", ".mp3", ".ogg"];

function isAllowed(name) {
  const ext = name.slice(name.lastIndexOf(".")).toLowerCase();
  return ALLOWED.includes(ext);
}

export default function UploadPanel({ onUpload, loading }) {
  const [files, setFiles] = useState([]);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const addFiles = (newFiles) => {
    const valid = Array.from(newFiles).filter(isAllowed);
    setFiles((prev) => [...prev, ...valid]);
  };

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    addFiles(e.dataTransfer.files);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleInputChange = (e) => {
    addFiles(e.target.files);
    e.target.value = "";
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (files.length === 0) return;
    onUpload(files);
  };

  return (
    <form onSubmit={handleSubmit} className="upload-panel">
      <h2>Загрузка аудио</h2>

      <div
        className={`dropzone ${dragOver ? "dropzone-active" : ""}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
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
