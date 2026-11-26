import axios from "axios";
import { API_BASE, INTERNAL_KEY } from "../lib/constants";

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json", "x-internal-key": INTERNAL_KEY },
  timeout: 30_000,
});

apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error("[API Error]", err.response?.status, err.config?.url);
    return Promise.reject(err);
  }
);

export async function apiGet<T>(url: string): Promise<T> {
  const r = await apiClient.get<T>(url);
  return r.data;
}
export async function apiPost<T>(url: string, body?: unknown): Promise<T> {
  const r = await apiClient.post<T>(url, body);
  return r.data;
}
