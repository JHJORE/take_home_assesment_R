export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function pdfUrl(code: string): string {
  return `${API_BASE}/policy/${encodeURIComponent(code)}/pdf`;
}
