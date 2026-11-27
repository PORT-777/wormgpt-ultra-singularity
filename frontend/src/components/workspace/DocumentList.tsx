export function DocumentList({ docs }: { docs: string[] }) {
  if (!docs.length)
    return (
      <div className="border-t p-4 text-xs text-muted-foreground">
        No documents in this workspace yet.
      </div>
    );
  return (
    <div className="border-t p-4">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Documents
      </div>
      <ul className="space-y-1">
        {docs.map((d, i) => (
          <li key={`${d}-${i}`} className="truncate text-sm">
            {d}
          </li>
        ))}
      </ul>
    </div>
  );
}
