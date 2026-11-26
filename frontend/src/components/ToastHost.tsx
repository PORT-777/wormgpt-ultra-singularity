import { useEffect, useState } from "react";
type Toast = { id: number; text: string };
export function ToastHost() {
  const [items, setItems] = useState<Toast[]>([]);
  useEffect(() => {
    const handler = (e: Event) => {
      const text = (e as CustomEvent<string>).detail;
      const id = Date.now(); setItems(v => [...v, { id, text }]);
      setTimeout(() => setItems(v => v.filter(t => t.id !== id)), 4000);
    };
    window.addEventListener("platform-toast", handler);
    return () => window.removeEventListener("platform-toast", handler);
  }, []);
  return <div className="fixed bottom-4 right-4 z-50 space-y-2">{items.map(t => <div key={t.id} className="rounded-lg border bg-background px-4 py-2 text-sm shadow-lg">{t.text}</div>)}</div>;
}
export function toast(text: string) { window.dispatchEvent(new CustomEvent("platform-toast", { detail: text })); }
