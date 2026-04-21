export const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type Product = {
  id: string;
  name: string;
  slug: string;
  tagline: string;
  short_description: string;
  supported_os: string[];
  status: string;
};

export async function apiGet<T>(path: string, token?: string): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    next: { revalidate: 60 }
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}
