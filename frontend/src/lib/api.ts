export const API_BASE = "http://localhost:5000/api";

export async function apiFetch(
    path: string,
    options: RequestInit = {}
): Promise<Response> {
    const token = localStorage.getItem("access_token");

    return fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
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