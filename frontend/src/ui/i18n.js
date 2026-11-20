// @ts-nocheck
/**
 * Minimal runtime language switch for the new shell.
 * App calls setUiLang() during render, so every child that reads t()
 * renders with the current language on the same pass.
 */
let current = "ar";

export function setUiLang(lang) {
  current = lang === "en" ? "en" : "ar";
}

export function uiLang() {
  return current;
}

/** t("عربي", "English") */
export function t(ar, en) {
  return current === "ar" ? ar : en;
}