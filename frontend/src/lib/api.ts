const rawApiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5000/api";
export const API_BASE = rawApiBase.replace(/\/$/, "").endsWith("/api")
    ? rawApiBase.replace(/\/$/, "")
    : `${rawApiBase.replace(/\/$/, "")}/api`;

export async function apiFetch(
    path: string,
    options: RequestInit = {}
): Promise<Response> {
    const token = localStorage.getItem("access_token");
    const isFormData = options.body instanceof FormData;

    return fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
            ...(!isFormData ? { "Content-Type": "application/json" } : {}),
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...options.headers,
        },
    });
}

export async function apiJson<T>(
    path: string,
    options: RequestInit = {}
): Promise<T> {
    const res = await apiFetch(path, options);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Something went wrong");
    return data as T;
}
