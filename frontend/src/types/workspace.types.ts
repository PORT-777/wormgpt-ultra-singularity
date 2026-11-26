export interface WorkspaceInfo {
  id: string; name: string; description: string; vector_collection: string;
  documents: string[]; llm_model: string; llm_temperature: number;
  similarity_threshold: number; top_k_docs: number; created_at: string;
}
