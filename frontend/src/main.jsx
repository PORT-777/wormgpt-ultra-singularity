// @ts-nocheck
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import { ToastProvider } from "./components/Toast.jsx";
import "./index.css";
import "./styles/theme.css";
import "./styles/shell.css";
import "./markdown.css";
import "./accessibility.css";
import "./ui/port777-polish.css";

// Bust stale SW caches from older builds. An old worker can keep serving an
// index.html that references JS chunks which no longer exist -> black screen.
const SW_VERSION = "port777-shell-v2";
if ("serviceWorker" in navigator && import.meta.env.PROD) {
  (async () => {
    try {
      const staled = localStorage.getItem("port777_sw_version") !== SW_VERSION;
      if (staled) {
        const regs = await navigator.serviceWorker.getRegistrations();
        for (const reg of regs) await reg.unregister();
        localStorage.setItem("port777_sw_version", SW_VERSION);
        if (regs.length) {
          window.location.reload();
          return;
        }
      }
      window.addEventListener("load", () => {
        navigator.serviceWorker.register("/sw.js").catch(() => {});
      });
    } catch {
      // Service worker is optional — the app must still boot without it.
    }
  })();
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ToastProvider>
      <App />
    </ToastProvider>
  </React.StrictMode>
);


