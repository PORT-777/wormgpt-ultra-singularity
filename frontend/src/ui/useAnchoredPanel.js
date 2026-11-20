// @ts-nocheck
import { useLayoutEffect, useState } from "react";

/**
 * Position a floating panel (menu/popover) next to an anchor element and keep
 * it inside the viewport. Uses position:fixed so parent `overflow:hidden`
 * (e.g. the composer) cannot clip it.
 *
 * @param {boolean} open
 * @param {object} anchorRef  ref of the button/wrapper the panel belongs to
 * @param {{width?:number, align?:"start"|"end", gap?:number}} opts
 */
export function useAnchoredPanel(open, anchorRef, { width = 260, align = "start", gap = 8 } = {}) {
  const [pos, setPos] = useState(null);

  useLayoutEffect(() => {
    if (!open) { setPos(null); return; }
    const update = () => {
      const el = anchorRef?.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const w = Math.min(width, Math.max(180, vw - 24));
      let left = align === "end" ? r.right - w : r.left;
      left = Math.min(Math.max(12, left), vw - w - 12);
      const spaceAbove = r.top - 12;
      const spaceBelow = vh - r.bottom - 12;
      const up = spaceAbove > 340 || spaceAbove >= spaceBelow;
      setPos({
        position: "fixed",
        left,
        width: w,
        minWidth: 0,
        right: "auto",
        top: up ? "auto" : r.bottom + gap,
        bottom: up ? vh - r.top + gap : "auto",
        maxHeight: Math.min(560, Math.max(180, up ? spaceAbove : spaceBelow)),
        overflowY: "auto",
      });
    };
    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [open, anchorRef, width, align, gap]);

  return pos;
}