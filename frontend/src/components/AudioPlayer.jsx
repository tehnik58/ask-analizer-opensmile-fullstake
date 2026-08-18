import { useEffect, useRef, useState, useCallback } from "react";
import { Howl } from "howler";
import { audioUrl } from "../api";

export default function AudioPlayer({ src, label, onTimeUpdate }) {
  const soundRef = useRef(null);
  const rafRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    const sound = new Howl({
      src: [audioUrl(src)],
      html5: true,
      onload: () => setDuration(sound.duration()),
      onend: () => {
        setPlaying(false);
        cancelAnimationFrame(rafRef.current);
      },
    });
    soundRef.current = sound;
    return () => {
      sound.unload();
      cancelAnimationFrame(rafRef.current);
    };
  }, [src]);

  const tick = useCallback(() => {
    if (soundRef.current && soundRef.current.playing()) {
      const t = soundRef.current.seek();
      setCurrentTime(t);
      if (onTimeUpdate) onTimeUpdate(t);
      rafRef.current = requestAnimationFrame(tick);
    }
  }, [onTimeUpdate]);

  const toggle = () => {
    const sound = soundRef.current;
    if (!sound) return;
    if (playing) {
      sound.pause();
      cancelAnimationFrame(rafRef.current);
    } else {
      sound.play();
      rafRef.current = requestAnimationFrame(tick);
    }
    setPlaying(!playing);
  };

  const seek = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    const t = pct * duration;
    soundRef.current?.seek(t);
    setCurrentTime(t);
  };

  const fmt = (s) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
  };

  const pct = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div className="audio-player">
      {label && <span className="player-label">{label}</span>}
      <button onClick={toggle} className="play-btn">
        {playing ? "⏸" : "▶"}
      </button>
      <div className="timeline" onClick={seek}>
        <div className="timeline-fill" style={{ width: `${pct}%` }} />
        <div className="timeline-handle" style={{ left: `${pct}%` }} />
      </div>
      <span className="time">
        {fmt(currentTime)} / {fmt(duration)}
      </span>
    </div>
  );
}
