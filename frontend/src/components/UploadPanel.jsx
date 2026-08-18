import { useState } from "react";

export default function UploadPanel({ onUpload, loading }) {
  const [files, setFiles] = useState([]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (files.length === 0) return;
    onUpload(files);
  };

  return (
    <form onSubmit={handleSubmit} className="upload-panel">
      <h2>Загрузка аудио</h2>
      <div className="upload-row">
        <label>
          Записи:
          <input
            type="file"
            accept=".wav,.mp3,.ogg"
            multiple
            onChange={(e) => setFiles(Array.from(e.target.files))}
          />
        </label>
        {files.length > 0 && (
          <span className="filename">
            {files.map((f) => f.name).join(", ")}
          </span>
        )}
      </div>
      <button type="submit" disabled={files.length === 0 || loading}>
        {loading ? "Анализ..." : "Анализировать"}
      </button>
    </form>
  );
}
