import { useState } from "react";

export default function UploadPanel({ onUpload, loading }) {
  const [original, setOriginal] = useState(null);
  const [translations, setTranslations] = useState([]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!original || translations.length === 0) return;
    onUpload(original, translations);
  };

  return (
    <form onSubmit={handleSubmit} className="upload-panel">
      <h2>Загрузка аудио</h2>
      <div className="upload-row">
        <label>
          Оригинал:
          <input
            type="file"
            accept=".wav,.mp3,.ogg"
            onChange={(e) => setOriginal(e.target.files[0])}
          />
        </label>
        {original && <span className="filename">{original.name}</span>}
      </div>
      <div className="upload-row">
        <label>
          Переводы:
          <input
            type="file"
            accept=".wav,.mp3,.ogg"
            multiple
            onChange={(e) => setTranslations(Array.from(e.target.files))}
          />
        </label>
        {translations.length > 0 && (
          <span className="filename">
            {translations.map((f) => f.name).join(", ")}
          </span>
        )}
      </div>
      <button type="submit" disabled={!original || translations.length === 0 || loading}>
        {loading ? "Анализ..." : "Анализировать"}
      </button>
    </form>
  );
}
