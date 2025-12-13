import { apiFetch } from "./api";
import { refreshToken } from "./auth";

export async function protectedFetch(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  let res = await apiFetch(path, options);

  if (res.status === 401) {
    const refreshed = await refreshToken();
    if (!refreshed) throw new Error("Session expired");
    res = await apiFetch(path, options);
  }

  return res;
}
