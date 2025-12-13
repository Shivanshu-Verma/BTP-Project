import { apiFetch } from "./api";

export async function refreshToken(): Promise<boolean> {
  const res = await apiFetch("/auth/refresh/", { method: "POST" });
  return res.ok;
}

export async function logout(): Promise<void> {
  await apiFetch("/auth/logout/", { method: "POST" });
}
