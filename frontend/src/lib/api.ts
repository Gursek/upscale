import { drainOfflineQueue, enqueueInvoiceRequest } from "$lib/offline-queue";

const rawApiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5000/api";
export const API_BASE = rawApiBase.replace(/\/$/, "").endsWith("/api")
    ? rawApiBase.replace(/\/$/, "")
    : `${rawApiBase.replace(/\/$/, "")}/api`;

function normalizedMethod(options: RequestInit) {
    return String(options.method ?? "GET").toUpperCase();
}

function shouldQueueInvoiceRequest(path: string, options: RequestInit) {
    const normalizedPath = path.replace(/\/$/, "");
    return normalizedMethod(options) === "POST" && normalizedPath === "/invoices";
}

function shouldSkipRefresh(path: string) {
    return path.startsWith("/auth/login") ||
        path.startsWith("/auth/register") ||
        path.startsWith("/auth/password-reset") ||
        path.startsWith("/auth/refresh");
}

function clearTokensAndRedirect() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
    }
}

async function refreshAccessToken(): Promise<string | null> {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) return null;

    try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
            method: "POST",
            headers: {
                Authorization: `Bearer ${refreshToken}`,
            },
        });
        if (!response.ok) return null;
        const data = await response.json();
        if (!data.access_token) return null;
        localStorage.setItem("access_token", data.access_token);
        return data.access_token;
    } catch {
        return null;
    }
}

async function fetchWithAuth(path: string, options: RequestInit, token: string | null) {
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

export async function apiFetch(
    path: string,
    options: RequestInit = {}
): Promise<Response> {
    const token = localStorage.getItem("access_token");

    try {
        let response = await fetchWithAuth(path, options, token);
        if (response.status === 401 && !shouldSkipRefresh(path)) {
            const refreshedToken = await refreshAccessToken();
            if (refreshedToken) {
                response = await fetchWithAuth(path, options, refreshedToken);
            } else {
                clearTokensAndRedirect();
            }
        }
        if (typeof navigator !== "undefined" && navigator.onLine) {
            void drainOfflineQueue(API_BASE, localStorage.getItem("access_token"));
        }
        return response;
    } catch (error) {
        if (shouldQueueInvoiceRequest(path, options)) {
            await enqueueInvoiceRequest({
                url: path,
                method: "POST",
                body: typeof options.body === "string" ? options.body : null,
                timestamp: Date.now(),
                retries: 0,
            });
            throw new Error("Offline. Invoice queued and will sync when connection is restored.");
        }
        throw error;
    }
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

export async function revokeCurrentSession() {
    const accessToken = localStorage.getItem("access_token");
    const refreshToken = localStorage.getItem("refresh_token");
    if (!accessToken) return;

    try {
        await fetch(`${API_BASE}/auth/logout`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${accessToken}`,
            },
            body: JSON.stringify({ refresh_token: refreshToken }),
        });
    } catch {
        // Local logout should still continue when the network is unavailable.
    }
}
