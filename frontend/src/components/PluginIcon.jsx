// @ts-nocheck
import React, { useState, useEffect, useCallback } from "react";
import Icon from "./Icon.jsx";
import { t } from "../ui/i18n.js";
import { GLYPH_ICONS } from "./pluginIcons.js";

/**
 * PluginIcon - Renders brand-aware icons for plugins.
 * Falls back to glyphs then emojis when no brand SVG is available.
 */
export default function PluginIcon({ id, icon, size = 24, radius = 6, ...props }) {
  const [imgError, setImgError] = useState(false);
  const [svgData, setSvgData] = useState(null);

  // Try to load brand icon from pluginIcons.js
  useEffect(() => {
    let cancelled = false;
    async function loadBrandIcon() {
      try {
        const mod = await import("./pluginIcons.js");
        const brand = mod.BRAND_ICONS?.[id];
        if (brand && brand.paths) {
          const pathsSvg = brand.paths.map((p, i) => `<path d="${p}" key="${i}"/>`).join("");
          const svg = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(
            `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="${size}" height="${size}"><rect width="24" height="24" fill="${brand.hex || "#CC0000"}" rx="4"/><g fill="#fff">${pathsSvg}</g></svg>`
          )}`;
          if (!cancelled) setSvgData(svg);
        }
      } catch {
        // module not available, fall through
      }
    }
    loadBrandIcon();
    return () => { cancelled = true; };
  }, [id, size]);

  // Brand SVG available
  if (svgData && !imgError) {
    return (
      <img
        src={svgData}
        alt={id}
        width={size}
        height={size}
        style={{
          borderRadius: radius,
          background: "#0A0A0A",
          border: "1px solid rgba(255,255,255,.08)",
        }}
        onError={() => setImgError(true)}
        {...props}
      />
    );
  }

  // Glyph fallback
  const glyph = GLYPH_ICONS?.[id];

  if (glyph) {
    return (
      <div
        style={{
          width: size,
          height: size,
          borderRadius: radius,
          background: `${glyph.hex}22`,
          border: `1px solid ${glyph.hex}55`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: glyph.hex,
          fontSize: size * 0.55,
          flexShrink: 0,
        }}
        title={id}
        {...props}
      >
        <Icon name={glyph.icon} size={Math.round(size * 0.5)} style={{ color: glyph.hex }} />
      </div>
    );
  }

  // Emoji fallback
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        background: "rgba(204,0,0,.1)",
        border: "1px solid rgba(204,0,0,.3)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: size * 0.55,
        flexShrink: 0,
      }}
      title={id}
      {...props}
    >
      {icon || "🔌"}
    </div>
  );
}