import { useDropzone } from "react-dropzone";
import { Upload } from "lucide-react";
import { cn } from "../../lib/utils";
export function FileDropzone({ onFiles }: { onFiles: (f: File[]) => void }) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop: onFiles });
  return <div {...getRootProps()} className={cn("cursor-pointer rounded-lg border-2 border-dashed p-6 text-center hover:border-primary/50", isDragActive && "border-primary bg-primary/5")}>
    <input {...getInputProps()} />
    <Upload className="mx-auto mb-2 text-muted-foreground" size={20} />
    <p className="text-sm font-medium">Drop files or click to upload</p>
    <p className="text-xs text-muted-foreground">PDF, DOCX, TXT, MD, HTML</p>
  </div>;
}
