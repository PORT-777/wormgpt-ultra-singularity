import { useRef, useState } from "react";
import { apiClient } from "../../api/client";

type UploadResult = { ok: boolean; path: string; size: number };

export function DocumentUpload({ workspaceId }: { workspaceId: string }) {
  const [busy, setBusy] = useState(false);
  const [uploaded, setUploaded] = useState<string[]>([]);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  async function onPick(files: FileList | null) {
    if (!files?.length || !workspaceId) return;
    setBusy(true);
    setError("");
    const names: string[] = [];
    try {
      for (const file of Array.from(files)) {
        const form = new FormData();
        form.append("file", file, file.name);
        const r = await apiClient.post<UploadResult>("/api/files/upload", form, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        if (r.data?.ok) names.push(file.name);
        else setError("Upload rejected by the server.");
      }
      setUploaded((prev) => [...prev, ...names]);
    } catch {
      setError("Upload failed — check the backend connection.");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="space-y-2 p-4">
      <label className="flex cursor-pointer items-center justify-center rounded-md border border-dashed px-3 py-4 text-sm text-muted-foreground transition-colors hover:bg-muted/50">
        {busy ? "Uploading…" : "Click to upload documents"}
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => onPick(e.target.files)}
          disabled={busy}
        />
      </label>
      {uploaded.length > 0 && (
        <div className="text-xs text-muted-foreground">
          Uploaded: {uploaded.join(", ")}
        </div>
      )}
      {error && <div className="text-xs text-destructive">{error}</div>}
    </div>
  );
}
