// @ts-nocheck
import React, { useCallback, useEffect, useState } from "react";
import Icon from "./Icon.jsx";
import { award, getState } from "../gamification.js";

/**
 * Compact XP / level widget shown in the top bar.
 * Listens for "xxxgpt:xp" window events (fired by tools + chat) and
 * awards XP through the backend, with an offline localStorage fallback.
 */
export default function XPBar({ onOpen }) {
  const [st, setSt] = useState(null);
  const [floats, setFloats] = useState([]);
  const [flash, setFlash] = useState(false);

  const refresh = useCallback(async () => {
    try { setSt(await getState()); } catch { /* offline */ }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  useEffect(() => {
    const onXp = async (e) => {
      const ev = e?.detail?.event;
      if (!ev) return;
      const prevLevel = st?.level || 0;
      try {
        const next = await award(ev, { amount: e.detail.amount, meta: e.detail.meta });
        if (!next) return;
        setSt(next);
        if (next.awarded) {
          const id = `${Date.now()}-${Math.random()}`;
          setFloats((f) => [...f, { id, xp: next.awarded }]);
        }
        if (next.level > prevLevel && prevLevel > 0) {
          setFlash(true);
          setTimeout(() => setFlash(false), 1200);
        }
      } catch { /* ignore */ }
    };
    window.addEventListener("xxxgpt:xp", onXp);
    return () => window.removeEventListener("xxxgpt:xp", onXp);
  }, [st?.level]);

  useEffect(() => {
    const t = setInterval(refresh, 60000);
    return () => clearInterval(t);
  }, [refresh]);

  if (!st) return null;
  const pct = Math.max(0, Math.min(100, Number(st.progress) || 0));
  return (
    <>
      <button
        type="button"
        className={`xp-bar ${flash ? "levelup" : ""}`}
        onClick={onOpen}
        title={`Level ${st.level} ${st.level_name} · ${st.xp} XP · streak ${st.streak}d · ${st.achievements_unlocked}/${st.achievements_total} achievements${st.source === "local" ? " (offline cache)" : ""}`}
        aria-label={`Level ${st.level} ${st.level_name}, ${st.xp} XP. Open progress dashboard`}
      >
        <span className="xp-level"><Icon name="spark" size={11} />L{st.level}</span>
        <span className="xp-track" aria-hidden="true"><i style={{ width: `${pct}%` }} /></span>
        <span className="xp-meta">{st.next_level_xp > 0 ? `${st.xp}/${st.next_level_xp}` : `${st.xp} XP`}</span>
        {floats.map((f) => (
          <span
            key={f.id}
            className="xp-float"
            onAnimationEnd={() => setFloats((list) => list.filter((x) => x.id !== f.id))}
          >+{f.xp} XP</span>
        ))}
      </button>
      {flash && <div className="levelup-flash" aria-hidden="true" />}
    </>
  );
}
