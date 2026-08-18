import { useEffect, useRef, useState, useCallback } from "react";
import { Howl } from "howler";
import { audioUrl } from "../api";

function fmt(s) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
}

export default function AudioPlayer({ src, label, onTimeUpdate, duration: durationProp }) {
  const soundRef = useRef(null);
  const rafRef = useRef(null);
  const fillRef = useRef(null);
  const handleRef = useRef(null);
  const timeRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [duration, setDuration] = useState(durationProp || 0);

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

  const updateImperatively = useCallback((t, dur) => {
    const pct = dur > 0 ? (t / dur) * 100 : 0;
    if (fillRef.current) fillRef.current.style.width = `${pct}%`;
    if (handleRef.current) handleRef.current.style.left = `${pct}%`;
    if (timeRef.current) timeRef.current.textContent = `${fmt(t)} / ${fmt(dur)}`;
    if (onTimeUpdate) onTimeUpdate(t, dur);
  }, [onTimeUpdate]);

  const tick = useCallback(() => {
    if (soundRef.current && soundRef.current.playing()) {
      const t = soundRef.current.seek();
      const dur = soundRef.current.duration();
      updateImperatively(t, dur);
      rafRef.current = requestAnimationFrame(tick);
    }
  }, [updateImperatively]);

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
    const dur = soundRef.current?.duration() || duration;
    const t = pct * dur;
    soundRef.current?.seek(t);
    updateImperatively(t, dur);
  };

  return (
    <div className="audio-player">
      {label && <span className="player-label">{label}</span>}
      <button onClick={toggle} className="play-btn">
        {playing ? "⏸" : "▶"}
      </button>
      <div className="timeline" onClick={seek}>
        <div ref={fillRef} className="timeline-fill" style={{ width: "0%" }} />
        <div ref={handleRef} className="timeline-handle" style={{ left: "0%" }} />
      </div>
      <span ref={timeRef} className="time">
        {fmt(0)} / {fmt(duration)}
      </span>
    </div>
  );
}
