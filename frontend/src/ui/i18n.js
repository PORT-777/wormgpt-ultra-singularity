// @ts-nocheck
/**
 * Runtime language layer for the shell.
 * Every t(ar, en, fr, es, de, tr) call uses the active language; when a
 * translation is not provided it falls back to the English string.
 */
export const LANGUAGES = [
  { id: "ar", label: "العربية", dir: "rtl" },
  { id: "en", label: "English", dir: "ltr" },
  { id: "fr", label: "Français", dir: "ltr" },
  { id: "es", label: "Español", dir: "ltr" },
  { id: "de", label: "Deutsch", dir: "ltr" },
  { id: "tr", label: "Türkçe", dir: "ltr" },
];

let current = "ar";

export function setUiLang(lang) {
  current = LANGUAGES.some((l) => l.id === lang) ? lang : "ar";
}

export function uiLang() {
  return current;
}

export function uiDir() {
  return current === "ar" ? "rtl" : "ltr";
}

const DICT = {
  fr: {
    "New chat": "Nouvelle discussion", "Settings": "Paramètres", "Search conversations": "Rechercher des discussions",
    "Active project": "Projet actif", "No project": "Aucun projet", "Select": "Choisir", "Clear": "Effacer",
    "Attach files": "Joindre des fichiers", "Send": "Envoyer", "Stop generating": "Arrêter la génération",
    "Ready": "Prêt", "Working…": "Travail en cours…", "Conversation": "Conversation", "New conversation": "Nouvelle conversation",
    "Sessions": "Sessions", "Files": "Fichiers", "Memory": "Mémoire", "Saved prompts": "Promptes enregistrés",
    "Plugins & integrations": "Extensions et intégrations", "Models & providers": "Modèles et fournisseurs",
    "AI Agents": "Agents IA", "Activity & traces": "Activité et traces", "Advanced": "Avancé", "Advanced tools": "Outils avancés",
    "Security tools": "Outils de sécurité", "Export chat": "Exporter la discussion", "Extensions (MCP)": "Extensions (MCP)",
    "Vendored repos": "Dépôts intégrés", "Light mode": "Mode clair", "Dark mode": "Mode sombre",
    "Conversations": "Conversations", "Local workspace": "Espace de travail local", "Offline": "Hors ligne",
    "Full access: on": "Accès complet : activé", "Full access: off": "Accès complet : désactivé",
    "Analyze project": "Analyser le projet", "Analyze binary": "Analyser le binaire", "Code quality": "Qualité du code",
    "Static analysis": "Analyse statique", "Search": "Rechercher", "Refresh": "Actualiser", "No project selected": "Aucun projet sélectionné",
    "Enter to send · Shift+Enter for a new line": "Entrée pour envoyer · Maj+Entrée pour un saut de ligne",
    "Working. press Esc to stop": "Travail en cours. Appuyez sur Échap pour arrêter.",
    "Working… press Esc to stop": "Travail en cours… Appuyez sur Échap pour arrêter.",
    "Generating — you can stop at any time": "Génération en cours — vous pouvez arrêter à tout moment",
    "Backend disconnected": "Connexion au serveur perdue", "Reconnecting to the workspace…": "Reconnexion à l'espace de travail…",
    "Retry": "Réessayer", "Resend": "Renvoyer", "Stop": "Arrêter", "Copy": "Copier", "Edit": "Modifier",
    "Rename": "Renommer", "Duplicate": "Dupliquer", "Delete": "Supprimer", "Cancel": "Annuler",
  },
  es: {
    "New chat": "Nuevo chat", "Settings": "Ajustes", "Search conversations": "Buscar conversaciones",
    "Active project": "Proyecto activo", "No project": "Sin proyecto", "Select": "Seleccionar", "Clear": "Limpiar",
    "Attach files": "Adjuntar archivos", "Send": "Enviar", "Stop generating": "Detener generación",
    "Ready": "Listo", "Working…": "Trabajando…", "Conversation": "Conversación", "New conversation": "Nueva conversación",
    "Sessions": "Sesiones", "Files": "Archivos", "Memory": "Memoria", "Saved prompts": "Promptos guardados",
    "Plugins & integrations": "Complementos e integraciones", "Models & providers": "Modelos y proveedores",
    "AI Agents": "Agentes IA", "Activity & traces": "Actividad y trazas", "Advanced": "Avanzado", "Advanced tools": "Herramientas avanzadas",
    "Security tools": "Herramientas de seguridad", "Export chat": "Exportar chat", "Extensions (MCP)": "Extensiones (MCP)",
    "Vendored repos": "Repositorios integrados", "Light mode": "Modo claro", "Dark mode": "Modo oscuro",
    "Conversations": "Conversaciones", "Local workspace": "Espacio de trabajo local", "Offline": "Sin conexión",
    "Full access: on": "Acceso completo: activado", "Full access: off": "Acceso completo: desactivado",
    "Analyze project": "Analizar proyecto", "Analyze binary": "Analizar binario", "Code quality": "Calidad del código",
    "Static analysis": "Análisis estático", "Search": "Buscar", "Refresh": "Actualizar", "No project selected": "Ningún proyecto seleccionado",
    "Enter to send · Shift+Enter for a new line": "Intro para enviar · Mayús+Intro para nueva línea",
    "Working. press Esc to stop": "Trabajando. Pulsa Esc para detener.",
    "Working… press Esc to stop": "Trabajando… Pulsa Esc para detener.",
    "Generating — you can stop at any time": "Generando — puedes detener en cualquier momento",
    "Backend disconnected": "Conexión con el servidor perdida", "Reconnecting to the workspace…": "Reconectando al espacio de trabajo…",
    "Retry": "Reintentar", "Resend": "Reenviar", "Stop": "Detener", "Copy": "Copiar", "Edit": "Editar",
    "Rename": "Renombrar", "Duplicate": "Duplicar", "Delete": "Eliminar", "Cancel": "Cancelar",
  },
  de: {
    "New chat": "Neuer Chat", "Settings": "Einstellungen", "Search conversations": "Konversationen suchen",
    "Active project": "Aktives Projekt", "No project": "Kein Projekt", "Select": "Auswählen", "Clear": "Löschen",
    "Attach files": "Dateien anhängen", "Send": "Senden", "Stop generating": "Generierung stoppen",
    "Ready": "Bereit", "Working…": "Arbeitet…", "Conversation": "Konversation", "New conversation": "Neue Konversation",
    "Sessions": "Sitzungen", "Files": "Dateien", "Memory": "Speicher", "Saved prompts": "Gespeicherte Prompts",
    "Plugins & integrations": "Plugins & Integrationen", "Models & providers": "Modelle & Anbieter",
    "AI Agents": "KI-Agenten", "Activity & traces": "Aktivität & Spuren", "Advanced": "Erweitert", "Advanced tools": "Erweiterte Werkzeuge",
    "Security tools": "Sicherheitswerkzeuge", "Export chat": "Chat exportieren", "Extensions (MCP)": "Erweiterungen (MCP)",
    "Vendored repos": "Eingebundene Repositories", "Light mode": "Helles Design", "Dark mode": "Dunkles Design",
    "Conversations": "Konversationen", "Local workspace": "Lokaler Arbeitsbereich", "Offline": "Offline",
    "Full access: on": "Vollzugriff: an", "Full access: off": "Vollzugriff: aus",
    "Analyze project": "Projekt analysieren", "Analyze binary": "Binärdatei analysieren", "Code quality": "Codequalität",
    "Static analysis": "Statische Analyse", "Search": "Suchen", "Refresh": "Aktualisieren", "No project selected": "Kein Projekt ausgewählt",
    "Enter to send · Shift+Enter for a new line": "Enter zum Senden · Shift+Enter für neue Zeile",
    "Working. press Esc to stop": "Arbeitet. Esc zum Stoppen.",
    "Working… press Esc to stop": "Arbeitet… Esc zum Stoppen.",
    "Generating — you can stop at any time": "Generierung — jederzeit stoppbar",
    "Backend disconnected": "Verbindung zum Server getrennt", "Reconnecting to the workspace…": "Verbindung zum Arbeitsbereich wird wiederhergestellt…",
    "Retry": "Erneut versuchen", "Resend": "Erneut senden", "Stop": "Stopp", "Copy": "Kopieren", "Edit": "Bearbeiten",
    "Rename": "Umbenennen", "Duplicate": "Duplizieren", "Delete": "Löschen", "Cancel": "Abbrechen",
  },
  tr: {
    "New chat": "Yeni sohbet", "Settings": "Ayarlar", "Search conversations": "Sohbetleri ara",
    "Active project": "Aktif proje", "No project": "Proje yok", "Select": "Seç", "Clear": "Temizle",
    "Attach files": "Dosya ekle", "Send": "Gönder", "Stop generating": "Üretimi durdur",
    "Ready": "Hazır", "Working…": "Çalışıyor…", "Conversation": "Sohbet", "New conversation": "Yeni sohbet",
    "Sessions": "Oturumlar", "Files": "Dosyalar", "Memory": "Bellek", "Saved prompts": "Kaydedilen promptlar",
    "Plugins & integrations": "Eklentiler ve entegrasyonlar", "Models & providers": "Modeller ve sağlayıcılar",
    "AI Agents": "Yapay zekâ ajanları", "Activity & traces": "Etkinlik ve izler", "Advanced": "Gelişmiş", "Advanced tools": "Gelişmiş araçlar",
    "Security tools": "Güvenlik araçları", "Export chat": "Sohbeti dışa aktar", "Extensions (MCP)": "Uzantılar (MCP)",
    "Vendored repos": "Dahil edilen depolar", "Light mode": "Açık tema", "Dark mode": "Koyu tema",
    "Conversations": "Sohbetler", "Local workspace": "Yerel çalışma alanı", "Offline": "Çevrimdışı",
    "Full access: on": "Tam erişim: açık", "Full access: off": "Tam erişim: kapalı",
    "Analyze project": "Projeyi analiz et", "Analyze binary": "İkili dosyayı analiz et", "Code quality": "Kod kalitesi",
    "Static analysis": "Statik analiz", "Search": "Ara", "Refresh": "Yenile", "No project selected": "Proje seçilmedi",
    "Enter to send · Shift+Enter for a new line": "Göndermek için Enter · yeni satır için Shift+Enter",
    "Working. press Esc to stop": "Çalışıyor. Durdurmak için Esc.",
    "Working… press Esc to stop": "Çalışıyor… Durdurmak için Esc.",
    "Generating — you can stop at any time": "Üretiliyor — istediğiniz zaman durdurabilirsiniz",
    "Backend disconnected": "Sunucu bağlantısı kesildi", "Reconnecting to the workspace…": "Çalışma alanına yeniden bağlanılıyor…",
    "Retry": "Yeniden dene", "Resend": "Yeniden gönder", "Stop": "Durdur", "Copy": "Kopyala", "Edit": "Düzenle",
    "Rename": "Yeniden adlandır", "Duplicate": "Çoğalt", "Delete": "Sil", "Cancel": "İptal",
  },
};

Object.assign(DICT.fr, {
  "Connect": "Connecter", "Details": "Détails", "Manual setup": "Configuration manuelle",
  "No auth required": "Aucune authentification requise", "Official": "Officiel", "tools": "outils", "scopes": "portées",
});
Object.assign(DICT.es, {
  "Connect": "Conectar", "Details": "Detalles", "Manual setup": "Configuración manual",
  "No auth required": "Sin autenticación", "Official": "Oficial", "tools": "herramientas", "scopes": "ámbitos",
});
Object.assign(DICT.de, {
  "Connect": "Verbinden", "Details": "Details", "Manual setup": "Manuelle Einrichtung",
  "No auth required": "Keine Authentifizierung nötig", "Official": "Offiziell", "tools": "Werkzeuge", "scopes": "Bereiche",
});
Object.assign(DICT.tr, {
  "Connect": "Bağlan", "Details": "Ayrıntılar", "Manual setup": "Manuel kurulum",
  "No auth required": "Kimlik doğrulama gerekmiyor", "Official": "Resmî", "tools": "araç", "scopes": "kapsam",
});

/** t("عربي", "English", "Français", "Español", "Deutsch", "Türkçe") */
export function t(ar, en, ...rest) {
  if (current === "ar") return ar;
  if (current === "en") return en;
  const idx = LANGUAGES.findIndex((l) => l.id === current) - 2;
  if (idx >= 0 && rest[idx]) return rest[idx];
  return DICT[current]?.[en] || DICT[current]?.[ar] || en;
}
