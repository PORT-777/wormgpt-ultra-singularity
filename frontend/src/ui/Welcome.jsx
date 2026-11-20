// @ts-nocheck
import React from "react";
import Icon from "../components/Icon.jsx";
import { t } from "./i18n.js";

const SUGGESTIONS = [
  { icon: "edit", title: t("اكتب", "Write"), desc: t("صُغ رسالة أو مقالًا أو مستندًا", "Draft an email, article, or document"), prompt: "Write a " },
  { icon: "code", title: t("برمج", "Code"), desc: t("ابنِ ميزة أو أصلح خطأً", "Build a feature or fix a bug"), prompt: "Write code to " },
  { icon: "globe", title: t("ابحث", "Research"), desc: t("اشرح موضوعًا مع المصادر", "Explain a topic with sources"), prompt: "Research " },
  { icon: "database", title: t("حلّل", "Analyze"), desc: t("لخّص ملفًا أو مجموعة بيانات", "Summarize a file or dataset"), prompt: "Analyze the attached file and " },
];

export default function Welcome({ onPick, model, userName }) {
  return (
    <div className="welcome">
      <div className="mark" aria-hidden="true">P7</div>
      <h1>{t("من أين نبدأ؟", "Where should we start?")}</h1>
      <p>{t("اسأل عن أي شيء، ابنِ شيئًا، أو أفلِت ملفًا. يضع PORT 777 الأدوات التي تحتاجها في متناولك — دون ضجيج.", "Ask anything, build something, or drop a file. PORT 777 keeps the tools you need close — without the noise.")}</p>

      <div className="suggestions" role="list">
        {SUGGESTIONS.map((s) => (
          <button key={s.title} type="button" className="sugg" role="listitem" onClick={() => onPick?.(s.prompt)}>
            <span className="si"><Icon name={s.icon} size={15} /></span>
            <span>
              <span className="st" style={{ display: "block" }}>{s.title}</span>
              <span className="sd" style={{ display: "block" }}>{s.desc}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}