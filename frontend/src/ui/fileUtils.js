// @ts-nocheck
/** Shared helpers for the Files & Artifacts views. */

const SKIP_DIRS = new Set([
  "__pycache__", "node_modules", ".git", ".pytest_cache", ".pytest_tmp",
  ".mypy_cache", ".ruff_cache", ".venv", "venv", "env", ".idea", ".vscode",
  "site-packages", "dist", "build", ".next", "target", "coverage",
]);

const SKIP_EXT = [".pyc", ".pyo", ".pyd", ".log", ".tmp", ".swp", ".swo", ".map", ".tsbuildinfo"];

/** Files that are never useful in the artifact list. */
export function isSkippedFile(f) {
  if (!f || f.is_dir) return false;
  const name = String(f.name || f.path || "");
  const lower = name.toLowerCase();
  if (SKIP_EXT.some(ext => lower.endsWith(ext))) return true;
  if (lower === "thumbs.db" || lower === "desktop.ini") return true;
  // skip anything inside caches / environments / build output
  const segs = String(f.path || f.name || "").replace(/\\/g, "/").toLowerCase().split("/");
  if (segs.slice(0, -1).some(s => SKIP_DIRS.has(s))) return true;
  return false;
}

/**
 * Flatten + filter + sort the /api/files payload.
 * Directories come first, then files, each alphabetically.
 */
export function cleanFileList(payload) {
  const raw = Array.isArray(payload) ? payload : (payload?.files || []);
  const list = raw.filter(f => f && !isSkippedFile(f));
  const dirs = list.filter(f => f.is_dir && !SKIP_DIRS.has(String(f.name).toLowerCase()));
  const files = list.filter(f => !f.is_dir);
  const byName = (a, b) => String(a.name || "").localeCompare(String(b.name || ""), "en", { sensitivity: "base" });
  return { dirs: dirs.sort(byName), files: files.sort(byName), hidden: raw.length - dirs.length - files.length };
}

export function formatSize(n) {
  const s = Number(n) || 0;
  if (s < 1024) return `${s} B`;
  if (s < 1024 * 1024) return `${Math.max(1, Math.round(s / 1024))} KB`;
  return `${(s / (1024 * 1024)).toFixed(1)} MB`;
}