// @ts-nocheck
import React, { useCallback, useEffect, useMemo, useState } from "react";
import Icon from "./Icon.jsx";
import PluginIcon from "./PluginIcon.jsx";
import { t } from "../ui/i18n.js";

/* ------------------------------------------------------------------ api ---- */

const TOKEN_KEY = "🔥😈 PORT 777 EVIL ☠️🔥👹_token";

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  const tok = localStorage.getItem(TOKEN_KEY);
  if (tok) headers.Authorization = `Bearer ${tok}`;
  if (opts.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
  const res = await fetch(path, { ...opts, headers, cache: "no-store" });
  const ct = res.headers.get("content-type") || "";
  const data = ct.includes("application/json")
    ? await res.json().catch(() => null)
    : await res.text().catch(() => null);
  if (!res.ok) {
    const msg = (data && (data.detail || data.error || data.message)) || `HTTP ${res.status}`;
    const err = new Error(String(typeof msg === "string" ? msg : JSON.stringify(msg)));
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

/* -------------------------------------------------------------- helpers ---- */

const CATEGORY_LABEL = {
  browser: ["متصفح", "Browser"],
  ai: ["ذكاء اصطناعي", "AI"],
  security: ["أمن", "Security"],
  siem: ["SIEM", "SIEM"],
  social: ["تواصل", "Social"],
  productivity: ["إنتاجية", "Productivity"],
  communication: ["اتصالات", "Communication"],
  devops: ["DevOps", "DevOps"],
  cloud: ["سحابة", "Cloud"],
  finance: ["مالية", "Finance"],
  marketing: ["تسويق", "Marketing"],
  data: ["بيانات", "Data"],
  custom: ["مخصص", "Custom"],
};

const catLabel = (c) => {
  const pair = CATEGORY_LABEL[c];
  return pair ? t(pair[0], pair[1]) : c || "—";
};

const STATUS = {
  connected: {
    ar: "متصل",
    en: "Connected",
    color: "var(--ok)",
    bg: "var(--ok-bg)",
    border: "var(--ok-border)",
  },
  not_connected: {
    ar: "غير متصل",
    en: "Not connected",
    color: "var(--muted)",
    bg: "transparent",
    border: "var(--border)",
  },
  setup_required: {
    ar: "يتطلب إعداد OAuth",
    en: "OAuth setup required",
    color: "var(--warn)",
    bg: "rgba(245,158,11,.1)",
    border: "rgba(245,158,11,.4)",
  },
  connecting: {
    ar: "جارٍ الاتصال…",
    en: "Connecting…",
    color: "var(--accent-hover)",
    bg: "rgba(204,0,0,.12)",
    border: "rgba(204,0,0,.45)",
  },
  awaiting_authorization: {
    ar: "بانتظار التفويض",
    en: "Awaiting authorization",
    color: "var(--accent-hover)",
    bg: "rgba(204,0,0,.12)",
    border: "rgba(204,0,0,.45)",
  },
  connection_expired: {
    ar: "انتهت صلاحية الاتصال",
    en: "Connection expired",
    color: "var(--warn)",
    bg: "rgba(245,158,11,.1)",
    border: "rgba(245,158,11,.4)",
  },
  authorization_failed: {
    ar: "فشل التفويض",
    en: "Authorization failed",
    color: "var(--danger-fg)",
    bg: "var(--err-bg)",
    border: "var(--err-border)",
  },
  permission_denied: {
    ar: "تم رفض الإذن",
    en: "Permission denied",
    color: "var(--danger-fg)",
    bg: "var(--err-bg)",
    border: "var(--err-border)",
  },
  unsupported: {
    ar: "OAuth غير متاح",
    en: "OAuth not available",
    color: "var(--muted)",
    bg: "var(--bg-2)",
    border: "var(--border)",
  },
  no_auth_required: {
    ar: "لا يحتاج مصادقة",
    en: "No auth required",
    color: "var(--muted)",
    bg: "var(--bg-2)",
    border: "var(--border)",
  },
};

function statusMeta(status) {
  return STATUS[status] || STATUS.not_connected;
}

const REASON = {
  permission_denied: [
    "تم رفض الإذن من المزود. لم يتم ربط الحساب.",
    "The provider denied permission. Nothing was connected.",
  ],
  provider_not_configured: [
    "معرّف/سر عميل OAuth غير مضبوط على الخادم.",
    "The OAuth client id/secret is not configured on the server.",
  ],
  invalid_state: [
    "جلسة التفويض غير صالحة أو انتهت. ابدأ من جديد.",
    "The authorization session is invalid or expired. Start again.",
  ],
  expired_state: [
    "انتهت مهلة جلسة التفويض. ابدأ من جديد.",
    "The authorization session timed out. Start again.",
  ],
  token_exchange_failed: [
    "رفض المزود تبادل رمز التفويض.",
    "The provider rejected the authorization-code exchange.",
  ],
  oauth_not_supported: [
    "هذا المزود لا يدعم OAuth 2.0 للأدوات المطلوبة.",
    "This provider has no OAuth 2.0 flow for the requested tools.",
  ],
  authorization_failed: [
    "فشل التفويض. راجع السجلات أو أعد المحاولة.",
    "Authorization failed. Check the server log or retry.",
  ],
};

function reasonLabel(reason) {
  const pair = REASON[reason];
  return pair ? t(pair[0], pair[1]) : reason || t("فشل التفويض", "Authorization failed");
}

function credentialFields(plugin) {
  const cfg = plugin?.auth_config || {};
  const order = [
    "api_key_field",
    "token_field",
    "url_field",
    "webhook_url_field",
    "host_field",
    "port_field",
    "user_field",
    "from_field",
  ];
  const out = [];
  const seen = new Set();

  const push = (key, label) => {
    if (!key || seen.has(key)) return;
    seen.add(key);
    const isSecret = /(api_?key|token|secret|password|pass$)/i.test(key) && !/url|host/i.test(key);
    out.push({
      key,
      label: label.replace(/_/g, " "),
      secret: isSecret,
      numeric: /port/.test(key),
    });
  };

  order.forEach((metaKey) => {
    if (cfg[metaKey]) push(cfg[metaKey], metaKey.replace(/_field$/, ""));
  });
  Object.entries(cfg).forEach(([k, v]) => {
    if (typeof v === "string" && k.endsWith("_field")) push(v, k.replace(/_field$/, ""));
  });
  if (Array.isArray(cfg.extra_fields)) {
    cfg.extra_fields.forEach((k) => {
      if (typeof k === "string") push(k, k);
    });
  }

  return out;
}

function authLabel(plugin) {
  if (plugin.oauth_supported) return "OAuth 2.0";
  if (plugin.auth_type === "none") return t("بدون مصادقة", "No auth");
  if (plugin.auth_type === "webhook") return "Webhook";
  if (plugin.auth_type === "apikey") return t("مفتاح API", "API key");
  return plugin.auth_type || "—";
}

function StatusPill({ status }) {
  const meta = statusMeta(status);
  return (
    <span
      style={{
        padding: "3px 8px",
        borderRadius: 999,
        fontSize: 9.5,
        letterSpacing: ".05em",
        textTransform: "uppercase",
        color: meta.color,
        background: meta.bg,
        border: `1px solid ${meta.border}`,
        whiteSpace: "nowrap",
        fontWeight: 600,
      }}
    >
      {t(meta.ar, meta.en)}
    </span>
  );
}

function ScopeChips({ scopes, limit = 8 }) {
  const list = Array.isArray(scopes) ? scopes : [];
  if (!list.length) return null;
  return (
    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
      {list.slice(0, limit).map((s) => (
        <span key={s} className="pl-chip" style={{ cursor: "default", fontSize: 10 }}>
          {s}
        </span>
      ))}
      {list.length > limit && (
        <span className="pl-chip" style={{ cursor: "default", fontSize: 10 }}>
          +{list.length - limit}
        </span>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- panel ---- */

export default function PluginsPanel({ notify }) {
  const [items, setItems] = useState([]);
  const [counts, setCounts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("all");
  const [onlyConnected, setOnlyConnected] = useState(false);
  const [busyId, setBusyId] = useState("");
  const [pending, setPending] = useState({});
  const [detail, setDetail] = useState(null);
  const [testResult, setTestResult] = useState(null);
  const [manualFor, setManualFor] = useState(null);
  const [creds, setCreds] = useState({});

  /* ----------------------------- Phase 3: health + history + auto-reconnect ---- */
  const [health, setHealth] = useState(null);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [autoReconnect, setAutoReconnect] = useState(true);
  const [healthRefreshedAt, setHealthRefreshedAt] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const [showHealth, setShowHealth] = useState(false);

  const say = useCallback(
    (msg, kind = "info") => {
      try {
        notify?.(msg, kind);
      } catch {
        /* notify is optional */
      }
    },
    [notify]
  );

  const loadHealth = useCallback(
    async (opts = {}) => {
      const { silent = false, refresh = false, window = 900 } = opts;
      if (!silent) setHealthRefreshedAt(null);
      try {
        const data = await api(
          `/api/integrations/health?refresh=${refresh ? "true" : "false"}&window=${window}`
        );
        setHealth(data);
        setHealthRefreshedAt(new Date().toISOString());
        return data;
      } catch (e) {
        if (!silent) {
          say(t(" failed to load health", " failed to load health"), "warn");
        }
        return null;
      }
    },
    [say]
  );

  const loadHistory = useCallback(
    async (pluginId = null, limit = 50) => {
      setHistoryLoading(true);
      try {
        const qs = pluginId
          ? `?plugin_id=${encodeURIComponent(pluginId)}&limit=${limit}`
          : `?limit=${limit}`;
        const data = await api(`/api/integrations/history${qs}`);
        setHistory(data.events || []);
      } catch (e) {
        say(t(" failed to load history", " failed to load history"), "warn");
      } finally {
        setHistoryLoading(false);
      }
    },
    [say]
  );

  /* --------------------------------------------------------------- loading -- */

  const load = useCallback(async () => {
    setError("");
    try {
      const data = await api("/api/integrations");
      const list = Array.isArray(data?.integrations) ? data.integrations : [];
      setItems(list);
      setCounts(data?.counts || null);
      setDetail((current) => {
        if (!current) return current;
        return list.find((p) => p.id === current.id) || current;
      });
      setPending((prev) => {
        const next = { ...prev };
        list.forEach((item) => {
          if (next[item.id] === "awaiting_authorization" && item.status === "connected") {
            delete next[item.id];
          }
        });
        return next;
      });

      // Pull health + history in parallel so the UI stays fresh without a
      // second round trip.
      loadHealth({ silent: true });
      loadHistory(null, 50);
    } catch (e) {
      setError(e.message || String(e));
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [loadHealth, loadHistory]);

  useEffect(() => {
    load();
  }, [load]);

  /* ---------------------------------------------------- callback + popup -- */

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const integration = params.get("integration");
    if (!integration) return;

    const plugin = params.get("plugin") || "";
    const account = params.get("account") || "";
    if (integration === "connected") {
      say(
        t(`تم ربط ${plugin}${account ? ` بحساب ${account}` : ""}`,
          `${plugin} connected${account ? ` as ${account}` : ""}`),
        "ok"
      );
    } else {
      say(`${t("فشل ربط", "Connection failed")} ${plugin}: ${reasonLabel(params.get("reason"))}`, "error");
    }

    ["integration", "plugin", "account", "reason", "detail"].forEach((k) => params.delete(k));
    const qs = params.toString();
    window.history.replaceState(
      {},
      "",
      window.location.pathname + (qs ? `?${qs}` : "") + window.location.hash
    );
  }, [say]);

  useEffect(() => {
    const onMessage = (event) => {
      if (event.origin !== window.location.origin) return;
      const data = event.data;
      if (!data || data.type !== "wormgpt-integration" || !data.plugin) return;
      const pluginId = data.plugin;
      if (data.status === "connected") {
        setPending((prev) => ({ ...prev, [pluginId]: "connecting" }));
        say(
          t(`تم ربط ${pluginId}${data.account ? ` بحساب ${data.account}` : ""}`,
            `${pluginId} connected${data.account ? ` as ${data.account}` : ""}`),
          "ok"
        );
        load();
        setTimeout(() => {
          setPending((prev) => {
            const next = { ...prev };
            delete next[pluginId];
            return next;
          });
        }, 1400);
      } else {
        const reason = data.reason === "permission_denied" ? "permission_denied" : "authorization_failed";
        setPending((prev) => ({ ...prev, [pluginId]: reason }));
        say(
          `${t("فشل ربط", "Connection failed")} ${pluginId}: ${reasonLabel(data.reason)}`,
          "error"
        );
      }
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [load, say]);

  // Poll while at least one popup is awaiting authorization.
  useEffect(() => {
    const awaiting = Object.values(pending).some((s) => s === "awaiting_authorization");
    if (!awaiting) return undefined;
    const timer = setInterval(() => load(), 2600);
    return () => clearInterval(timer);
  }, [pending, load]);

  // Auto-reconnect: proactively refresh tokens that are about to expire so
  // the agent engine never hits an expired token mid-call.
  useEffect(() => {
    if (!autoReconnect) return undefined;
    const timer = setInterval(() => {
      loadHealth({ silent: true, refresh: true, window: 900 });
    }, 60_000);
    return () => clearInterval(timer);
  }, [autoReconnect, loadHealth]);

  /* -------------------------------------------------------------- derived -- */

  const categories = useMemo(() => {
    const set = new Set(items.map((p) => p.category).filter(Boolean));
    const order = [
      "ai",
      "social",
      "productivity",
      "communication",
      "devops",
      "cloud",
      "security",
      "siem",
      "data",
      "finance",
      "marketing",
      "browser",
      "custom",
    ];
    const ranked = Array.from(set).sort((a, b) => {
      const ia = order.indexOf(a);
      const ib = order.indexOf(b);
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
    });
    return ["all", ...ranked];
  }, [items]);

  const visible = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return items.filter((p) => {
      if (cat !== "all" && p.category !== cat) return false;
      if (onlyConnected && p.status !== "connected") return false;
      if (!needle) return true;
      const haystack = `${p.name} ${p.id} ${p.description || ""} ${(p.tags || []).join(" ")}`.toLowerCase();
      return haystack.includes(needle);
    });
  }, [items, q, cat, onlyConnected]);

  const liveCounts = useMemo(() => {
    const c = counts || {};
    return {
      total: c.total ?? items.length,
      oauth: c.oauth_supported ?? items.filter((p) => p.oauth_supported).length,
      configured: c.configured ?? 0,
      connected: items.filter((p) => p.status === "connected").length,
      expired: items.filter((p) => p.status === "connection_expired").length,
      expiring: c.expiring ?? 0,
      needs_attention: c.needs_attention ?? 0,
      setup_required: c.setup_required ?? 0,
    };
  }, [counts, items]);

  const statusFor = (item) => pending[item.id] || item.status || "not_connected";

  /* -------------------------------------------------------------- actions -- */

  const change = (id, body) => {
    setItems((prev) => prev.map((p) => (p.id === id ? { ...p, ...body } : p)));
    setDetail((d) => (d && d.id === id ? { ...d, ...body } : d));
  };

  const connect = (plugin) => {
    if (!plugin.oauth_supported) return;
    if (plugin.setup_required) {
      const missing = (plugin.oauth && plugin.oauth.missing_config) || [];
      say(
        t(
          `أضف ${missing.join(" و ") || "بيانات عميل OAuth"} إلى backend/.env أولاً`,
          `Add ${missing.join(" and ") || "the OAuth client credentials"} to backend/.env first`
        ),
        "warn"
      );
      setDetail(plugin);
      return;
    }

    const returnTo = window.location.pathname + window.location.search;
    const url =
      `/api/integrations/${encodeURIComponent(plugin.id)}/connect` +
      `?popup=1&return_to=${encodeURIComponent(returnTo)}`;

    setPending((prev) => ({ ...prev, [plugin.id]: "awaiting_authorization" }));
    let popup = null;
    try {
      popup = window.open(
        url,
        `wormgpt-oauth-${plugin.id}`,
        "width=540,height=720,menubar=no,toolbar=no,location=no,status=no"
      );
    } catch {
      popup = null;
    }

    if (!popup) {
      window.location.assign(url.replace("popup=1", "popup=0"));
      return;
    }

    const timer = setInterval(() => {
      if (popup.closed) {
        clearInterval(timer);
        setPending((prev) => {
          if (prev[plugin.id] !== "awaiting_authorization") return prev;
          const next = { ...prev };
          delete next[plugin.id];
          return next;
        });
        load();
      }
    }, 1200);
  };

  const disconnect = async (plugin) => {
    if (
      !window.confirm(
        t(`فصل ${plugin.name} وحذف الرموز المشفّرة؟`, `Disconnect ${plugin.name} and delete stored tokens?`)
      )
    ) {
      return;
    }
    setBusyId(plugin.id);
    try {
      await api(`/api/integrations/${encodeURIComponent(plugin.id)}/disconnect`, {
        method: "POST",
        body: JSON.stringify({ user_id: "default_user", revoke: true }),
      });
      change(plugin.id, { status: "not_connected", connection: null, account: null });
      setPending((prev) => {
        const next = { ...prev };
        delete next[plugin.id];
        return next;
      });
      say(t(`تم فصل ${plugin.name}`, `${plugin.name} disconnected`), "ok");
      await load();
    } catch (e) {
      say(t("فشل الفصل", "Disconnect failed") + ": " + e.message, "error");
    } finally {
      setBusyId("");
    }
  };

  const refreshToken = async (plugin) => {
    setBusyId(plugin.id);
    try {
      await api(`/api/integrations/${encodeURIComponent(plugin.id)}/refresh`, {
        method: "POST",
        body: JSON.stringify({ user_id: "default_user" }),
      });
      say(t("تم تحديث الرمز", "Token refreshed"), "ok");
      await load();
    } catch (e) {
      say(t("فشل تحديث الرمز", "Refresh failed") + ": " + e.message, "error");
    } finally {
      setBusyId("");
    }
  };

  const testConnection = async (plugin) => {
    setBusyId(plugin.id);
    setTestResult(null);
    try {
      const r = await api(`/api/integrations/${encodeURIComponent(plugin.id)}/test`, {
        method: "POST",
        body: JSON.stringify({ user_id: "default_user" }),
      });
      setTestResult(r);
      const ok = r?.status === "ok" || r?.status === "success" || r?.status === "connected";
      say(ok ? t("الاتصال ناجح", "Connection OK") : t("الاتصال فشل", "Connection failed"), ok ? "ok" : "error");
    } catch (e) {
      setTestResult({ status: "error", message: e.message });
      say(t("فشل الاختبار", "Test failed") + ": " + e.message, "error");
    } finally {
      setBusyId("");
    }
  };

  const install = async (plugin) => {
    setBusyId(plugin.id);
    try {
      await api(`/api/plugins/install/${encodeURIComponent(plugin.id)}`, { method: "POST" });
      change(plugin.id, { is_installed: true, is_enabled: true });
      await api(`/api/plugins/toggle/${encodeURIComponent(plugin.id)}?enable=true`, { method: "POST" }).catch(() => {});
      say(t(`تم تثبيت ${plugin.name}`, `${plugin.name} installed`), "ok");
      await load();
    } catch (e) {
      say(t("فشل التثبيت", "Install failed") + ": " + e.message, "error");
    } finally {
      setBusyId("");
    }
  };

  const toggle = async (plugin, enable) => {
    setBusyId(plugin.id);
    try {
      await api(
        `/api/plugins/toggle/${encodeURIComponent(plugin.id)}?enable=${enable ? "true" : "false"}`,
        { method: "POST" }
      );
      change(plugin.id, { is_enabled: enable });
      say(
        enable
          ? t(`تم تفعيل ${plugin.name}`, `${plugin.name} enabled`)
          : t(`تم تعطيل ${plugin.name}`, `${plugin.name} disabled`),
        "ok"
      );
      await load();
    } catch (e) {
      say(t("فشل التغيير", "Toggle failed") + ": " + e.message, "error");
    } finally {
      setBusyId("");
    }
  };

  const uninstall = async (plugin) => {
    if (
      !window.confirm(
        t(`إزالة ${plugin.name} وحذف بيانات الاعتماد؟`, `Uninstall ${plugin.name} and wipe credentials?`)
      )
    ) {
      return;
    }
    setBusyId(plugin.id);
    try {
      await api(`/api/plugins/uninstall/${encodeURIComponent(plugin.id)}`, { method: "DELETE" });
      change(plugin.id, { is_installed: false, is_enabled: false });
      if (detail?.id === plugin.id) setDetail(null);
      say(t(`تمت إزالة ${plugin.name}`, `${plugin.name} uninstalled`), "ok");
      await load();
    } catch (e) {
      say(t("فشل الحذف", "Uninstall failed") + ": " + e.message, "error");
    } finally {
      setBusyId("");
    }
  };

  const openManual = (plugin) => {
    const seed = {};
    credentialFields(plugin).forEach((f) => {
      seed[f.key] = "";
    });
    setCreds(seed);
    setManualFor(plugin);
  };

  const submitManual = async () => {
    if (!manualFor) return;
    const fields = credentialFields(manualFor);
    const missing = fields.filter((f) => !String(creds[f.key] || "").trim());
    if (missing.length) {
      say(t("أكمل كل الحقول المطلوبة", "Fill every required field"), "warn");
      return;
    }
    setBusyId(manualFor.id);
    try {
      await api(`/api/plugins/auth/${encodeURIComponent(manualFor.id)}`, {
        method: "POST",
        body: JSON.stringify({ credentials: creds }),
      });
      if (!manualFor.is_installed) {
        await api(`/api/plugins/install/${encodeURIComponent(manualFor.id)}`, { method: "POST" });
      }
      await api(`/api/plugins/toggle/${encodeURIComponent(manualFor.id)}?enable=true`, { method: "POST" });
      say(t("تم حفظ بيانات الاعتماد مشفّرة", "Credentials saved and encrypted"), "ok");
      setManualFor(null);
      await load();
    } catch (e) {
      say(t("فشل التحقق من البيانات", "Credential validation failed") + ": " + e.message, "error");
    } finally {
      setBusyId("");
    }
  };

  /* ---------------------------------------------------------------- states -- */

  if (loading) {
    return (
      <div style={{ display: "grid", gap: 10 }}>
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="ctx-card"
            style={{ height: 62, opacity: 0.55, animation: "pulse 1.4s ease-in-out infinite" }}
          />
        ))}
        <div style={{ color: "var(--muted)", fontSize: 12 }}>
          {t("جارٍ تحميل التكاملات…", "Loading integrations…")}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="ctx-card" style={{ borderColor: "var(--err-border)" }}>
        <h4>{t("نظام التكاملات غير متاح", "Integration system unavailable")}</h4>
        <div style={{ fontSize: 12.5, color: "var(--danger-fg)", marginBottom: 10 }}>{error}</div>
        <button type="button" className="btn sm" onClick={load}>
          <Icon name="refresh" size={13} />
          {t("إعادة المحاولة", "Retry")}
        </button>
      </div>
    );
  }

  /* ----------------------------------------------------------------- view -- */

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <style>{`
        .pl-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(255px,1fr)); gap:10px; }
        .pl-card { border:1px solid var(--border); border-radius:11px; background:var(--panel); padding:12px 13px; display:flex; flex-direction:column; gap:8px; min-height:168px; transition:border-color .15s, transform .15s; }
        .pl-card:hover { border-color:var(--border-2); }
        .pl-card.on { border-color:rgba(239,35,60,.45); box-shadow:inset 0 0 0 1px rgba(239,35,60,.14); }
        .pl-card.wait { border-color:rgba(204,0,0,.55); animation:pl-pulse 1.8s ease-in-out infinite; }
        @keyframes pl-pulse { 0%,100%{box-shadow:0 0 0 0 rgba(204,0,0,.0)} 50%{box-shadow:0 0 0 3px rgba(204,0,0,.12)} }
        .pl-chip { padding:3px 8px; border-radius:999px; border:1px solid var(--border); background:var(--bg-2); color:var(--muted); font-size:11px; cursor:pointer; transition:.15s; }
        .pl-chip:hover { color:var(--text); border-color:var(--border-2); }
        .pl-chip.on { background:rgba(239,35,60,.14); border-color:rgba(239,35,60,.45); color:#fff; }
        .pl-title { font-size:13px; font-weight:600; cursor:pointer; display:flex; align-items:center; gap:5px; }
        .pl-title:hover { color:var(--accent-hover); }
        .pl-desc { font-size:11.5px; color:var(--muted); line-height:1.5; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
        .pl-meta { font-size:10.5px; color:var(--muted); display:flex; align-items:center; gap:5px; flex-wrap:wrap; }
        .pl-account { font-size:11px; color:var(--ok); display:flex; align-items:center; gap:5px; min-width:0; }
        .pl-account span { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
        .pl-actions { display:flex; gap:6px; margin-top:auto; flex-wrap:wrap; align-items:center; }
        .pl-scroll { max-height:40vh; overflow:auto; padding-right:2px; }
        .pl-banner { display:flex; align-items:flex-start; gap:8px; padding:9px 11px; border-radius:9px; border:1px solid var(--border); background:var(--bg-2); font-size:11.5px; color:var(--muted); line-height:1.55; }
        .pl-detail-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:8px; }
        .pl-kv { border:1px solid var(--border); border-radius:8px; padding:7px 9px; background:var(--bg-2); min-width:0; }
        .pl-kv b { display:block; font-size:9.5px; letter-spacing:.07em; text-transform:uppercase; color:var(--muted); margin-bottom:3px; font-weight:600; }
        .pl-kv span { font-size:11.5px; color:var(--text-2); word-break:break-word; }
      `}</style>

      {/* stats */}
      <div className="ctx-card" style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Icon name="plug" size={16} />
          <strong style={{ fontSize: 13 }}>{t("التكاملات وربط الحسابات", "Integrations & account linking")}</strong>
        </div>
        <div style={{ display: "flex", gap: 12, fontSize: 11.5, color: "var(--muted)", flexWrap: "wrap" }}>
          <span>{t("متاح", "available")}: <b style={{ color: "var(--text)" }}>{liveCounts.total}</b></span>
          <span>OAuth: <b style={{ color: "var(--text)" }}>{liveCounts.oauth}</b></span>
          <span>{t("مُهيّأ", "configured")}: <b style={{ color: "var(--text)" }}>{liveCounts.configured}</b></span>
          <span>{t("متصل", "connected")}: <b style={{ color: "var(--ok)" }}>{liveCounts.connected}</b></span>
          <span>{t("منتهي", "expired")}: <b style={{ color: liveCounts.expired ? "var(--warn)" : "var(--text)" }}>{liveCounts.expired}</b></span>
          <span>{t("ينتهي قريباً", "expiring soon")}: <b style={{ color: liveCounts.expiring ? "var(--warn)" : "var(--text)" }}>{liveCounts.expiring}</b></span>
          <span>{t("يحتاج انتباه", "needs attention")}: <b style={{ color: liveCounts.needs_attention ? "var(--danger-fg)" : "var(--text)" }}>{liveCounts.needs_attention}</b></span>
          <span>{t("يتطلب الإعداد", "setup")}: <b style={{ color: liveCounts.setup_required ? "var(--warn)" : "var(--text)" }}>{liveCounts.setup_required}</b></span>
          {healthRefreshedAt && (
            <span style={{ opacity: 0.7 }}>
              · {t("تحديث صحة الاتصال", "health refresh")} {new Date(healthRefreshedAt).toLocaleTimeString()}
            </span>
          )}
        </div>
        <span style={{ flex: 1 }} />
        <button type="button" className="btn sm ghost" onClick={load} title={t("تحديث", "Refresh")}>
          <Icon name="refresh" size={13} />
          {t("تحديث", "Refresh")}
        </button>
        <button type="button" className="btn sm ghost" onClick={() => loadHealth({ silent: true, refresh: true, window: 900 })} title={t("تحديث صحة الاتصالات", "Refresh connection health")}>
          <Icon name="activity" size={13} />
          {t("صحة", "Health")}
        </button>
      </div>

      <div className="pl-banner">
        <Icon name="lock" size={14} style={{ flex: "0 0 auto", marginTop: 1, color: "var(--accent-hover)" }} />
        <div>
          {t(
            "اضغط «اتصال» لفتح صفحة تفويض المزود الرسمية. لا تُدخل كلمات المرور هنا ولا تُخزَّن الرموز في المتصفح — تُشفَّر على الخادم فقط.",
            "Click Connect to open the provider's official authorization page. Passwords are never entered here and tokens are never stored in the browser — they are encrypted server-side only."
          )}
        </div>
      </div>

      {/* filters */}
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <div className="model-search" style={{ flex: "1 1 220px", maxWidth: 340 }}>
          <Icon name="search" size={14} />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t("ابحث عن تكامل…", "Search integrations…")}
          />
        </div>
                <button
          type="button"
          className={`pl-chip ${onlyConnected ? "on" : ""}`}
          onClick={() => setOnlyConnected((v) => !v)}
        >
          {t("المتصل فقط", "Connected only")}
        </button>
        <button
          type="button"
          className={`pl-chip ${liveCounts.needs_attention ? "on" : ""}`}
          onClick={() => setOnlyConnected((v) => !v)}
          style={{ color: liveCounts.needs_attention ? "var(--danger-fg)" : undefined }}
        >
          {t("يحتاج انتباه", "Needs attention")}
        </button>
        <button
          type="button"
          className={`pl-chip ${showHealth ? "on" : ""}`}
          onClick={() => {
            setShowHealth((v) => !v);
            if (!showHealth) loadHealth({ silent: true, refresh: true, window: 900 });
          }}
        >
          <Icon name="activity" size={12} />
          {t("صحة الاتصالات", "Connection health")}
        </button>
        <button
          type="button"
          className={`pl-chip ${showHistory ? "on" : ""}`}
          onClick={() => {
            setShowHistory((v) => !v);
            if (!showHistory) loadHistory(null, 50);
          }}
        >
          <Icon name="clock" size={12} />
          {t("سجل الأحداث", "Audit trail")}
        </button>
        <label style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: "var(--muted)", cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={autoReconnect}
            onChange={(e) => setAutoReconnect(e.target.checked)}
            style={{ accentColor: "#CC0000" }}
          />
          {t("إعادة ربط تلقائي", "Auto-reconnect")}
        </label>
      </div>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {categories.map((c) => (
          <button
            key={c}
            type="button"
            className={`pl-chip ${cat === c ? "on" : ""}`}
            onClick={() => setCat(c)}
          >
            {c === "all" ? t("الكل", "All") : catLabel(c)}
          </button>
        ))}
      </div>

      {/* grid */}
      {visible.length === 0 ? (
        <div className="ctx-card" style={{ textAlign: "center", color: "var(--muted)", fontSize: 12.5 }}>
          {t("لا تكاملات تطابق البحث.", "No integrations match this filter.")}
        </div>
      ) : (
        <div className="pl-grid pl-scroll">
          {visible.map((p) => {
            const busy = busyId === p.id;
            const status = statusFor(p);
            const connected = status === "connected";
            const waiting = status === "awaiting_authorization" || status === "connecting";
            return (
              <div
                key={p.id}
                className={`pl-card ${connected ? "on" : ""} ${waiting ? "wait" : ""}`}
              >
                <div style={{ display: "flex", alignItems: "flex-start", gap: 9 }}>
                  <PluginIcon id={p.id} icon={p.icon} size={36} radius={9} />
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div className="pl-title" onClick={() => setDetail(p)} title={p.id}>
                      {p.name}
                      <Icon name="chevron" size={12} />
                    </div>
                    <div className="pl-meta" style={{ marginTop: 3 }}>
                      {catLabel(p.category)} · {authLabel(p)}
                    </div>
                  </div>
                  <StatusPill status={status} />
                </div>

                <div className="pl-desc">{p.description}</div>

                {connected && (p.account || p.account_email) && (
                  <div className="pl-account" title={p.account_email || p.account}>
                    <Icon name="check" size={12} />
                    <span>{p.account || p.account_email}</span>
                  </div>
                )}

                <div className="pl-meta">
                  <Icon name="activity" size={11} />
                  {t(`${p.tool_count ?? (p.tools || []).length} أداة`, `${p.tool_count ?? (p.tools || []).length} tools`)}
                  {p.oauth_supported && (p.scopes || []).length > 0 && (
                    <span>· {p.scopes.length} {t("صلاحية", "scopes")}</span>
                  )}
                  {p.is_official ? <span>· ✔ {t("رسمي", "official")}</span> : null}
                </div>

                <div className="pl-actions">
                  {connected ? (
                    <>
                      <button type="button" className="btn sm primary" disabled={busy} onClick={() => setDetail(p)}>
                        <Icon name="shield" size={11} />
                        {t("إدارة الصلاحيات", "Manage permissions")}
                      </button>
                      <button type="button" className="btn sm ghost" disabled={busy} onClick={() => disconnect(p)}>
                        {busy ? t("جارٍ…", "Working…") : t("فصل", "Disconnect")}
                      </button>
                    </>
                  ) : p.oauth_supported ? (
                    <>
                      <button
                        type="button"
                        className="btn sm primary"
                        disabled={busy || waiting || status === "setup_required"}
                        onClick={() => connect(p)}
                        title={
                          status === "setup_required"
                            ? t("أضف بيانات عميل OAuth إلى backend/.env", "Add OAuth client credentials to backend/.env")
                            : t("فتح صفحة تفويض المزود", "Open the provider authorization page")
                        }
                      >
                        <Icon name="link" size={11} />
                        {waiting
                          ? t("بانتظار التفويض…", "Awaiting authorization…")
                          : t("اتصال", "Connect")}
                      </button>
                      <button type="button" className="btn sm ghost" disabled={busy} onClick={() => setDetail(p)}>
                        {t("تفاصيل", "Details")}
                      </button>
                    </>
                  ) : p.status === "no_auth_required" ? (
                    <>
                      {!p.is_installed ? (
                        <button type="button" className="btn sm primary" disabled={busy} onClick={() => install(p)}>
                          {t("تثبيت", "Install")}
                        </button>
                      ) : (
                        <button
                          type="button"
                          className={`btn sm ${p.is_enabled ? "ghost" : "primary"}`}
                          disabled={busy}
                          onClick={() => toggle(p, !p.is_enabled)}
                        >
                          {p.is_enabled ? t("تعطيل", "Disable") : t("تفعيل", "Enable")}
                        </button>
                      )}
                      <button type="button" className="btn sm ghost" disabled={busy} onClick={() => setDetail(p)}>
                        {t("تفاصيل", "Details")}
                      </button>
                    </>
                  ) : (
                    <>
                      <button type="button" className="btn sm ghost" disabled={busy} onClick={() => openManual(p)}>
                        <Icon name="lock" size={11} />
                        {t("إعداد يدوي", "Manual setup")}
                      </button>
                      <button type="button" className="btn sm ghost" disabled={busy} onClick={() => setDetail(p)}>
                        {t("تفاصيل", "Details")}
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* detail drawer */}
      {detail && (
        <div className="ctx-card" style={{ borderColor: "rgba(239,35,60,.35)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <PluginIcon id={detail.id} icon={detail.icon} size={30} radius={8} />
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 600, display: "flex", alignItems: "center", gap: 7 }}>
                {detail.name}
                <StatusPill status={statusFor(detail)} />
              </div>
              <div style={{ fontSize: 10.5, color: "var(--muted)" }}>
                {detail.id} · v{detail.version || "1.0.0"} · {catLabel(detail.category)} · {authLabel(detail)}
              </div>
            </div>
            <span style={{ flex: 1 }} />
            <button type="button" className="mini-btn" onClick={() => setDetail(null)}>
              <Icon name="close" size={12} />
            </button>
          </div>

          <div style={{ fontSize: 12, color: "var(--text-2)", lineHeight: 1.6, marginBottom: 10 }}>
            {detail.long_description || detail.description}
          </div>

          {detail.oauth_supported && detail.oauth?.notes && (
            <div className="pl-banner" style={{ marginBottom: 10 }}>
              <Icon name="info" size={13} style={{ flex: "0 0 auto", marginTop: 1 }} />
              <div>{detail.oauth.notes}</div>
            </div>
          )}

          {!detail.oauth_supported && detail.oauth_reason && (
            <div className="pl-banner" style={{ marginBottom: 10, borderColor: "rgba(245,158,11,.35)" }}>
              <Icon name="info" size={13} style={{ flex: "0 0 auto", marginTop: 1, color: "var(--warn)" }} />
              <div>{detail.oauth_reason}</div>
            </div>
          )}

          <div className="pl-detail-grid" style={{ marginBottom: 10 }}>
            <div className="pl-kv">
              <b>{t("الحالة", "Status")}</b>
              <span>{t(statusMeta(statusFor(detail)).ar, statusMeta(statusFor(detail)).en)}</span>
            </div>
            <div className="pl-kv">
              <b>{t("الحساب", "Account")}</b>
              <span>{detail.account || detail.account_email || (detail.connection?.account?.email) || "—"}</span>
            </div>
            <div className="pl-kv">
              <b>{t("مساحة العمل", "Workspace")}</b>
              <span>{detail.connection?.account?.workspace || "—"}</span>
            </div>
            <div className="pl-kv">
              <b>{t("انتهاء الرمز", "Token expiry")}</b>
              <span>
                {detail.expires_at
                  ? new Date(detail.expires_at * 1000).toLocaleString()
                  : t("بدون انتهاء", "No expiry")}
              </span>
            </div>
            <div className="pl-kv">
              <b>{t("الأدوات", "Tools")}</b>
              <span>{detail.tool_count ?? (detail.tools || []).length}</span>
            </div>
            <div className="pl-kv">
              <b>{t("مُهيّأ على الخادم", "Server configured")}</b>
              <span>
                {detail.oauth_supported
                  ? detail.oauth?.configured
                    ? t("نعم", "Yes")
                    : t("لا — أضف بيانات العميل", "No — add client credentials")
                  : t("لا ينطبق", "N/A")}
              </span>
            </div>
          </div>

          {detail.oauth_supported && (
            <div style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: ".08em", color: "var(--muted)", marginBottom: 5 }}>
                {t("الصلاحيات المطلوبة", "Requested permissions")}
              </div>
              <ScopeChips scopes={detail.oauth?.scopes || []} limit={12} />
            </div>
          )}

          {detail.connection?.scopes?.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: ".08em", color: "var(--muted)", marginBottom: 5 }}>
                {t("الصلاحيات الممنوحة", "Granted permissions")}
              </div>
              <ScopeChips scopes={detail.connection.scopes} limit={12} />
            </div>
          )}

          {detail.connection?.last_error && (
            <div className="pl-banner" style={{ marginBottom: 10, borderColor: "rgba(245,158,11,.35)", color: "var(--warn)" }}>
              <Icon name="alert" size={13} style={{ flex: "0 0 auto", marginTop: 1 }} />
              <div>{detail.connection.last_error}</div>
            </div>
          )}

          {detail.connection && detail.connection.health && (
            <div className="pl-banner" style={{ marginBottom: 10, borderColor: "rgba(239,35,60,.35)" }}>
              <Icon name="activity" size={13} style={{ flex: "0 0 auto", marginTop: 1, color: "var(--accent-hover)" }} />
              <div style={{ display: "grid", gap: 6, width: "100%" }}>
                <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: 11 }}>
                  <span>{t("صحيحة", "healthy")}: <b style={{ color: detail.connection.health.healthy ? "var(--ok)" : "var(--danger-fg)" }}>{detail.connection.health.healthy ? t("نعم", "Yes") : t("لا", "No")}</b></span>
                  <span>{t("ينتهي في", "expires in")}: <b style={{ color: detail.connection.health.expiring_soon ? "var(--warn)" : "var(--text-2)" }}>{detail.connection.health.expires_in != null ? `${detail.connection.health.expires_in}s` : t("لا", "none")}</b></span>
                  <span>{t("تحديث تلقائي", "auto-refresh")}: <b style={{ color: detail.connection.health.auto_refresh ? "var(--ok)" : "var(--muted)" }}>{detail.connection.health.auto_refresh ? t("نعم", "Yes") : t("لا", "No")}</b></span>
                </div>
                <div style={{ fontSize: 10.5, color: "var(--muted)" }}>
                  {detail.connection.health.last_refreshed_at
                    ? t(" آخر:{} ", "last refresh: ") + detail.connection.health.last_refreshed_at
                    : t("لم يتم التحديث بعد", "no refresh yet")}
                </div>
              </div>
            </div>
          )}

          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
            <button type="button" className="btn sm ghost" onClick={() => { loadHistory(detail.id, 20); setShowHistory(true); }}>
              <Icon name="clock" size={12} />
              {t("سجل هذا الاتصال", "History for this connection")}
            </button>
            <button type="button" className="btn sm ghost" onClick={() => loadHealth({ silent: true, refresh: true, window: 900 })}>
              <Icon name="activity" size={12} />
              {t("تحديث صحة الاتصال", "Refresh health")}
            </button>
          </div>

          <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: ".08em", color: "var(--muted)", marginBottom: 6 }}>
            {t("الأدوات المتاحة للوكيل", "Tools exposed to the agent")}
          </div>
          <div style={{ display: "grid", gap: 6, maxHeight: 220, overflow: "auto", marginBottom: 10 }}>
            {(detail.tools || []).map((tool) => (
              <div key={tool.name} className="file-row" style={{ alignItems: "flex-start" }}>
                <code style={{ fontSize: 11, color: "var(--accent-hover)", whiteSpace: "nowrap" }}>{tool.name}</code>
                <span className="nm" style={{ color: "var(--text-2)", whiteSpace: "normal" }}>
                  {tool.description}
                </span>
              </div>
            ))}
            {!(detail.tools || []).length && (
              <div style={{ fontSize: 11.5, color: "var(--muted)" }}>{t("لا أدوات معلنة.", "No declared tools.")}</div>
            )}
          </div>

          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {detail.oauth_supported && statusFor(detail) !== "connected" && (
              <button
                type="button"
                className="btn sm primary"
                disabled={busyId === detail.id || detail.setup_required || statusFor(detail) === "awaiting_authorization"}
                onClick={() => connect(detail)}
              >
                <Icon name="link" size={12} />
                {t("اتصال", "Connect")}
              </button>
            )}
            {detail.oauth_supported && statusFor(detail) === "connected" && (
              <>
                <button type="button" className="btn sm ghost" disabled={busyId === detail.id} onClick={() => testConnection(detail)}>
                  <Icon name="check" size={12} />
                  {t("اختبار الاتصال", "Test connection")}
                </button>
                <button type="button" className="btn sm ghost" disabled={busyId === detail.id} onClick={() => refreshToken(detail)}>
                  <Icon name="refresh" size={12} />
                  {t("تحديث الرمز", "Refresh token")}
                </button>
                <button type="button" className="btn sm ghost" disabled={busyId === detail.id} onClick={() => disconnect(detail)}>
                  {t("فصل الحساب", "Disconnect")}
                </button>
              </>
            )}
            {!detail.oauth_supported && detail.auth_type !== "none" && (
              <button type="button" className="btn sm ghost" onClick={() => openManual(detail)}>
                <Icon name="lock" size={12} />
                {t("إعداد يدوي (متقدم)", "Manual setup (advanced)")}
              </button>
            )}
            {detail.auth_type === "none" && (
              <>
                {!detail.is_installed ? (
                  <button type="button" className="btn sm primary" onClick={() => install(detail)}>
                    {t("تثبيت", "Install")}
                  </button>
                ) : (
                  <button
                    type="button"
                    className={`btn sm ${detail.is_enabled ? "ghost" : "primary"}`}
                    onClick={() => toggle(detail, !detail.is_enabled)}
                  >
                    {detail.is_enabled ? t("تعطيل", "Disable") : t("تفعيل", "Enable")}
                  </button>
                )}
              </>
            )}
            {detail.is_installed && (
              <button type="button" className="btn sm ghost" disabled={busyId === detail.id} onClick={() => uninstall(detail)}>
                <Icon name="trash" size={12} />
                {t("إزالة", "Uninstall")}
              </button>
            )}
            {detail.docs_url && (
              <a
                href={detail.docs_url}
                target="_blank"
                rel="noreferrer"
                className="btn sm ghost"
                style={{ textDecoration: "none" }}
              >
                {t("وثائق المزود", "Provider docs")}
              </a>
            )}
          </div>

          {testResult && (
            <pre
              dir="ltr"
              style={{
                marginTop: 8,
                marginBottom: 0,
                padding: 8,
                borderRadius: 8,
                background: "var(--code-bg, #0c0c0f)",
                border: "1px solid var(--border)",
                fontSize: 11,
                maxHeight: 150,
                overflow: "auto",
                whiteSpace: "pre-wrap",
              }}
            >
              {JSON.stringify(testResult, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* legacy manual setup - only for providers with no OAuth flow */}
      {manualFor && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,.62)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 90,
            padding: 16,
          }}
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setManualFor(null);
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            style={{
              width: "min(460px,100%)",
              background: "var(--panel)",
              border: "1px solid var(--border-2)",
              borderRadius: 12,
              padding: 16,
              display: "grid",
              gap: 10,
              boxShadow: "var(--shadow)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <PluginIcon id={manualFor.id} icon={manualFor.icon} size={40} radius={10} />
              <div>
                <div style={{ fontWeight: 600, fontSize: 13.5 }}>{manualFor.name}</div>
                <div style={{ fontSize: 10.5, color: "var(--muted)" }}>
                  {t("إعداد يدوي — المزود لا يدعم OAuth 2.0", "Manual setup — provider has no OAuth 2.0")}
                </div>
              </div>
              <span style={{ flex: 1 }} />
              <button type="button" className="icon-btn" onClick={() => setManualFor(null)}>
                <Icon name="close" size={15} />
              </button>
            </div>

            <div style={{ fontSize: 11.5, color: "var(--warn)", lineHeight: 1.55 }}>
              {manualFor.oauth_reason ||
                t(
                  "لا يوجد تدفق تفويض رسمي لهذا المزود. استخدم بيانات اعتماد يدوية.",
                  "No official authorization flow exists for this provider. Use manual credentials."
                )}
            </div>

            {credentialFields(manualFor).length === 0 && (
              <div style={{ fontSize: 12, color: "var(--muted)" }}>
                {t(
                  "هذا التكامل لا يعلن حقول بيانات اعتماد قابلة للإعداد من هنا.",
                  "This integration declares no credential fields configurable here."
                )}
              </div>
            )}

            {credentialFields(manualFor).map((f) => (
              <label key={f.key} style={{ display: "grid", gap: 4 }}>
                <span style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: ".07em", color: "var(--muted)" }}>
                  {f.label}
                </span>
                <input
                  className="input"
                  type={f.secret ? "password" : f.numeric ? "number" : "text"}
                  value={creds[f.key] || ""}
                  onChange={(e) => setCreds((c) => ({ ...c, [f.key]: e.target.value }))}
                  placeholder={f.secret ? "••••••••" : f.numeric ? "443" : "https://…"}
                  autoComplete="off"
                  dir={f.secret ? "ltr" : undefined}
                />
              </label>
            ))}

            <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
              <button
                type="button"
                className="btn primary"
                style={{ flex: 1 }}
                disabled={busyId === manualFor.id}
                onClick={submitManual}
              >
                <Icon name="check" size={13} />
                {busyId === manualFor.id ? t("جارٍ التحقق…", "Verifying…") : t("حفظ وتفعيل", "Save & enable")}
              </button>
              <button type="button" className="btn ghost" onClick={() => setManualFor(null)}>
                {t("إلغاء", "Cancel")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
